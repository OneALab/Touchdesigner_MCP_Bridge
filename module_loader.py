# MCP Bridge Module Loader v2.0
# Discovers and loads modules from the modules/ directory
# Run inside TouchDesigner after td_setup.py has created the core bridge
#
# Usage:
#   1. Run td_setup.py first to create /project1/mcp_bridge
#   2. Then run this script to load all modules

import json
import os
import sys
import traceback
import importlib

print("=" * 60)
print("MODULE LOADER v2.0 (2025-02-10)")
print("  If you see 'Modules directory not found' instead of")
print("  'Searching for modules directory...' then you are")
print("  running OLD CODE from the .tox file, not this script.")
print("=" * 60)

def load_modules():
    """Discover and load all modules from the modules/ directory."""

    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        print("ERROR: MCP Bridge not found. Run td_setup.py first.")
        return

    # Find modules directory
    # NOTE: __file__ inside a TD Text DAT resolves to the operator path
    # (e.g. C:\project1\...) not the filesystem path, so we can't rely on it.
    # We CANNOT use __file__ here. Instead we build candidates from:
    #   1. TD's project.folder (the folder where the .toe file lives)
    #   2. Hardcoded known locations
    #   3. User home directory fallback
    script_dir = None

    candidates = []

    # Try TD's project folder (where the .toe file is saved)
    try:
        pf = project.folder
        if pf:
            # _mcp_bridge might be a subfolder of the project folder
            candidates.append(os.path.join(pf, '_mcp_bridge'))
            # Or the project folder's parent might contain _mcp_bridge
            candidates.append(os.path.join(os.path.dirname(pf), '_mcp_bridge'))
            # Or modules/ might be directly inside the project folder
            candidates.append(pf)
    except Exception as e:
        print(f"  Note: Could not read project.folder: {e}")

    # Hardcoded known locations
    candidates.append(r"c:\Users\onea\Dropbox (Personal)\TouchDesigner\_mcp_bridge")
    candidates.append(os.path.join(os.path.expanduser("~"), "Dropbox (Personal)", "TouchDesigner", "_mcp_bridge"))

    # Also try the cache directory (for GitHub-fetched modules)
    try:
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            appdata = os.path.expanduser('~/Library/Application Support')
        candidates.append(os.path.join(appdata, 'TouchDesigner', 'mcp_bridge_cache'))
    except Exception:
        pass

    print(f"  Searching for modules directory...")
    for d in candidates:
        if d:
            mod_path = os.path.join(d, "modules")
            exists = os.path.exists(mod_path)
            print(f"    {'OK' if exists else '--'} {mod_path}")
            if exists and script_dir is None:
                script_dir = d

    if script_dir is None:
        print("ERROR: Cannot find modules directory.")
        print("Make sure the 'modules/' folder is in one of the searched locations above.")
        return

    modules_dir = os.path.join(script_dir, "modules")
    print(f"  Found modules at: {modules_dir}")

    # Add modules dir to Python path so imports work
    if modules_dir not in sys.path:
        sys.path.insert(0, modules_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Get or create module registry table
    registry = bridge.op('module_registry')
    if registry is None:
        registry = bridge.create(tableDAT, 'module_registry')
        registry.nodeX = -200
        registry.nodeY = -150
        registry.clear()
        registry.appendRow(['name', 'version', 'prefix', 'status', 'loaded_at', 'description'])

    # Clear existing entries (keep header)
    while registry.numRows > 1:
        registry.deleteRow(1)

    # Discover modules
    discovered = []
    for entry in sorted(os.listdir(modules_dir)):
        mod_dir = os.path.join(modules_dir, entry)
        init_file = os.path.join(mod_dir, "__init__.py")
        if os.path.isdir(mod_dir) and os.path.exists(init_file):
            try:
                # Import the module's __init__.py to get its manifest
                mod_name = entry
                if mod_name in sys.modules:
                    # Reload to pick up changes
                    importlib.reload(sys.modules[mod_name])
                    mod = sys.modules[mod_name]
                else:
                    mod = importlib.import_module(mod_name)

                manifest = getattr(mod, 'MODULE', None)
                if manifest is None:
                    print(f"  WARNING: {entry}/__init__.py has no MODULE manifest, skipping")
                    continue

                manifest['_dir'] = mod_dir
                manifest['_module_name'] = mod_name
                discovered.append(manifest)
            except Exception as e:
                print(f"  ERROR loading {entry}: {e}")
                traceback.print_exc()

    # Resolve dependencies (topological sort)
    ordered = resolve_dependencies(discovered)

    # Load each module
    import datetime
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    loaded_modules = {}
    for manifest in ordered:
        mod_name = manifest['name']
        prefix = manifest.get('prefix', f'/{mod_name}')
        version = manifest.get('version', '0.0.0')
        description = manifest.get('description', '')

        print(f"  Loading module: {mod_name} (v{version}) -> {prefix}")

        try:
            # Import the handler
            handler_path = os.path.join(manifest['_dir'], 'handler.py')
            if not os.path.exists(handler_path):
                print(f"    WARNING: No handler.py found for {mod_name}")
                registry.appendRow([mod_name, version, prefix, 'no_handler', now, description])
                continue

            handler_module_name = f"{manifest['_module_name']}.handler"
            if handler_module_name in sys.modules:
                importlib.reload(sys.modules[handler_module_name])
                handler = sys.modules[handler_module_name]
            else:
                handler = importlib.import_module(handler_module_name)

            # Call setup if it exists
            if hasattr(handler, 'setup'):
                handler.setup(bridge)
                print(f"    TD operators created")

            # Store handler reference for the routing system
            loaded_modules[mod_name] = {
                'handler': handler,
                'manifest': manifest,
                'prefix': prefix,
            }

            registry.appendRow([mod_name, version, prefix, 'loaded', now, description])
            print(f"    OK")

        except Exception as e:
            print(f"    ERROR: {e}")
            traceback.print_exc()
            registry.appendRow([mod_name, version, prefix, 'error', now, str(e)])

    # Store loaded modules in bridge storage for the router to access
    bridge.store('loaded_modules', loaded_modules)

    # Create or update the module router handler
    create_module_router(bridge, loaded_modules)

    print("")
    print("=" * 50)
    print(f"Module loading complete: {len(loaded_modules)}/{len(ordered)} modules loaded")
    print("=" * 50)
    print(f"Module API: http://127.0.0.1:9981")
    print(f"Loaded: {', '.join(loaded_modules.keys())}")
    print("=" * 50)


def resolve_dependencies(modules):
    """Topological sort of modules by dependencies."""
    by_name = {m['name']: m for m in modules}
    visited = set()
    ordered = []
    visiting = set()  # For cycle detection

    def visit(name):
        if name in visited:
            return
        if name in visiting:
            print(f"  WARNING: Circular dependency detected involving {name}")
            return
        visiting.add(name)

        mod = by_name.get(name)
        if mod is None:
            return

        for dep in mod.get('dependencies', []):
            if dep in by_name:
                visit(dep)
            else:
                print(f"  WARNING: {name} depends on {dep} which is not available")

        visiting.discard(name)
        visited.add(name)
        ordered.append(mod)

    for m in modules:
        visit(m['name'])

    return ordered


def create_module_router(bridge, loaded_modules):
    """Create the HTTP router that dispatches to module handlers."""

    # Get or create the module webserver on port 9981
    mod_ws = bridge.op('mod_webserver')
    if mod_ws is None:
        mod_ws = bridge.create(webserverDAT, 'mod_webserver')
        mod_ws.nodeX = 200
        mod_ws.nodeY = 0

    mod_ws.par.port = 9981
    mod_ws.par.active = True

    # Create the router handler
    router = bridge.op('mod_router')
    if router is None:
        router = bridge.create(textDAT, 'mod_router')
        router.nodeX = 200
        router.nodeY = -150

    # Build the router code
    # The router reads loaded_modules from bridge storage and dispatches requests
    router_code = '''# Module Router - dispatches HTTP requests to loaded module handlers
# Auto-generated by module_loader.py - do not edit directly
import json
import traceback

def parse_body(request):
    """Parse request body from POST data."""
    body = {}
    if request.get('data'):
        raw = request['data']
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        try:
            body = json.loads(raw)
        except:
            pass
    return body

def onHTTPRequest(webServerDAT, request, response):
    """Route requests to the appropriate module handler."""
    uri = request['uri']
    method = request.get('method', 'GET')
    body = parse_body(request)

    # CORS headers
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'

    if method == 'OPTIONS':
        response['statusCode'] = 200
        response['statusReason'] = 'OK'
        return response

    bridge = op('/project1/mcp_bridge')
    loaded_modules = bridge.fetch('loaded_modules', {})

    # Try each module's prefix
    for mod_name, mod_info in loaded_modules.items():
        prefix = mod_info['prefix']
        handler = mod_info['handler']

        # Check if URI matches this module's prefix
        if uri == prefix or uri.startswith(prefix + '/') or uri.startswith(prefix + '?'):
            try:
                # Call the module's on_request handler
                if hasattr(handler, 'on_request'):
                    result = handler.on_request(uri, method, body, request, response)

                    # If handler returned a response directly (e.g. binary data), use it
                    if result is None:
                        # Handler already modified response directly
                        return response

                    if isinstance(result, dict):
                        response['statusCode'] = 200
                        response['statusReason'] = 'OK'
                        response['Content-Type'] = 'application/json'
                        response['data'] = json.dumps(result, indent=2)
                        return response
                else:
                    response['statusCode'] = 501
                    response['statusReason'] = 'Not Implemented'
                    response['Content-Type'] = 'application/json'
                    response['data'] = json.dumps({'error': f'Module {mod_name} has no request handler'})
                    return response
            except Exception as e:
                response['statusCode'] = 500
                response['statusReason'] = 'Internal Server Error'
                response['Content-Type'] = 'application/json'
                response['data'] = json.dumps({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'module': mod_name
                })
                return response

    # No module matched - check for /ping
    if uri == '/ping':
        result = {
            'status': 'ok',
            'service': 'modules',
            'port': 9981,
            'modules': list(loaded_modules.keys())
        }
        response['statusCode'] = 200
        response['statusReason'] = 'OK'
        response['Content-Type'] = 'application/json'
        response['data'] = json.dumps(result, indent=2)
        return response

    # 404
    response['statusCode'] = 404
    response['statusReason'] = 'Not Found'
    response['Content-Type'] = 'application/json'
    available = [{'name': n, 'prefix': m['prefix']} for n, m in loaded_modules.items()]
    response['data'] = json.dumps({
        'error': f'Unknown endpoint: {uri}',
        'available_modules': available
    })
    return response


def onWebSocketOpen(webServerDAT, client, uri):
    """Route WebSocket connections to modules."""
    bridge = op('/project1/mcp_bridge')
    loaded_modules = bridge.fetch('loaded_modules', {})
    for mod_name, mod_info in loaded_modules.items():
        handler = mod_info['handler']
        if hasattr(handler, 'on_websocket_open'):
            try:
                handler.on_websocket_open(webServerDAT, client, uri)
            except:
                pass

def onWebSocketClose(webServerDAT, client):
    """Route WebSocket close to modules."""
    bridge = op('/project1/mcp_bridge')
    loaded_modules = bridge.fetch('loaded_modules', {})
    for mod_name, mod_info in loaded_modules.items():
        handler = mod_info['handler']
        if hasattr(handler, 'on_websocket_close'):
            try:
                handler.on_websocket_close(webServerDAT, client)
            except:
                pass

def onWebSocketReceiveText(webServerDAT, client, data):
    """Route WebSocket messages to modules."""
    bridge = op('/project1/mcp_bridge')
    loaded_modules = bridge.fetch('loaded_modules', {})
    for mod_name, mod_info in loaded_modules.items():
        handler = mod_info['handler']
        if hasattr(handler, 'on_websocket_receive'):
            try:
                handler.on_websocket_receive(webServerDAT, client, data)
            except:
                pass
'''

    router.text = router_code
    mod_ws.par.callbacks = 'mod_router'
    print("  Module router created on port 9981")


# Run
load_modules()
