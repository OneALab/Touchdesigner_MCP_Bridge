# UI Module Handler
# Web UI serving, component discovery, parameter schema, WebSocket
import json
import os
import traceback

# MIME types for static file serving
MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
}

# WebSocket clients
_WS_CLIENTS = {}

# Cached asset content
_ASSET_CACHE = {}


def setup(bridge_op):
    """Load UI assets into Text DATs for serving."""
    # Find assets directory — __file__ doesn't work in TD, so try multiple paths
    assets_dir = None

    candidates = []
    # Try __file__ (works when imported normally, not in TD Text DATs)
    try:
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(handler_dir, 'assets'))
    except NameError:
        pass
    # Try known repo locations
    candidates.append(os.path.join(
        r"c:\Users\onea\Dropbox (Personal)\TouchDesigner\_mcp_bridge",
        "modules", "mod_ui", "assets"))
    candidates.append(os.path.join(
        os.path.expanduser("~"), "Dropbox (Personal)", "TouchDesigner",
        "_mcp_bridge", "modules", "mod_ui", "assets"))
    # Try cache location
    try:
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        candidates.append(os.path.join(
            appdata, 'TouchDesigner', 'mcp_bridge_cache',
            'modules', 'mod_ui', 'assets'))
    except Exception:
        pass

    for candidate in candidates:
        if os.path.exists(candidate):
            assets_dir = candidate
            break

    if assets_dir:
        # Cache assets from files
        asset_files = {
            'index.html': 'ui_index',
            'styles.css': 'ui_styles',
            'app.js': 'ui_app',
            'controls.js': 'ui_controls',
            'preview.js': 'ui_preview',
        }
        for filename, dat_name in asset_files.items():
            filepath = os.path.join(assets_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    _ASSET_CACHE[dat_name] = f.read()
                print(f"    Loaded asset: {filename}")

    # Also try to load from existing Text DATs (for loader-based deployments)
    ui_container = bridge_op.op('ui')
    if ui_container:
        for dat_name in ['ui_index', 'ui_styles', 'ui_app', 'ui_controls', 'ui_preview']:
            dat = ui_container.op(dat_name)
            if dat and dat.text and dat_name not in _ASSET_CACHE:
                _ASSET_CACHE[dat_name] = dat.text


def scan_custom_parameters(comp_path):
    """Scan a COMP for custom parameters and return UI schema."""
    try:
        comp = op(comp_path)
        if comp is None:
            return {'error': f'Operator not found: {comp_path}'}
        if comp.family != 'COMP':
            return {'error': f'Not a COMP: {comp_path}'}

        ui_schema = {
            'success': True,
            'path': comp_path,
            'name': comp.name,
            'pages': []
        }

        for page in comp.customPages:
            page_data = {
                'name': page.name,
                'parameters': []
            }

            for par in page.pars:
                par_data = {
                    'name': par.name,
                    'label': par.label,
                    'style': par.style,
                    'default': par.default,
                    'value': par.eval(),
                    'readonly': par.readOnly,
                    'enable': par.enable,
                }
                if par.style in ('Float', 'Int'):
                    par_data['min'] = par.min if hasattr(par, 'min') else None
                    par_data['max'] = par.max if hasattr(par, 'max') else None
                    par_data['normMin'] = par.normMin if hasattr(par, 'normMin') else None
                    par_data['normMax'] = par.normMax if hasattr(par, 'normMax') else None
                    par_data['clampMin'] = par.clampMin if hasattr(par, 'clampMin') else False
                    par_data['clampMax'] = par.clampMax if hasattr(par, 'clampMax') else False
                elif par.style in ('Menu', 'StrMenu'):
                    par_data['menuNames'] = list(par.menuNames) if par.menuNames else []
                    par_data['menuLabels'] = list(par.menuLabels) if par.menuLabels else []

                page_data['parameters'].append(par_data)

            if page_data['parameters']:
                ui_schema['pages'].append(page_data)

        return ui_schema
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def discover_ui_components(parent_path='/project1', max_depth=3):
    """Find all COMPs with custom parameters under a path."""
    try:
        parent_op = op(parent_path)
        if parent_op is None:
            return {'error': f'Path not found: {parent_path}'}

        components = []
        for child in parent_op.findChildren(type=baseCOMP, maxDepth=max_depth):
            if child.customPages:
                par_count = sum(len(p.pars) for p in child.customPages)
                if par_count > 0:
                    components.append({
                        'path': child.path,
                        'name': child.name,
                        'pages': [p.name for p in child.customPages],
                        'parameterCount': par_count
                    })
        for child in parent_op.findChildren(type=containerCOMP, maxDepth=max_depth):
            if child.customPages:
                par_count = sum(len(p.pars) for p in child.customPages)
                if par_count > 0:
                    components.append({
                        'path': child.path,
                        'name': child.name,
                        'pages': [p.name for p in child.customPages],
                        'parameterCount': par_count
                    })

        return {'success': True, 'count': len(components), 'components': components}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def discover_ui_components_hierarchical(parent_path='/project1', max_depth=5):
    """Return nested tree of COMPs with custom parameters."""
    try:
        def get_custom_param_count(comp):
            count = 0
            for page in comp.customPages:
                count += len(page.pars)
            return count

        def get_custom_params_list(comp):
            params = []
            for page in comp.customPages:
                for par in page.pars:
                    if par.isCustom:
                        params.append({
                            'name': par.name,
                            'label': par.label,
                            'style': par.style
                        })
            return params

        def build_tree(comp, depth=0):
            if depth > max_depth:
                return None
            if 'mcp_bridge' in comp.path:
                return None

            param_count = get_custom_param_count(comp)
            params = get_custom_params_list(comp) if param_count > 0 else []

            node = {
                'path': comp.path,
                'name': comp.name,
                'type': comp.type,
                'paramCount': param_count,
                'params': params,
                'children': []
            }

            for child in comp.children:
                if child.family == 'COMP' and child.type in ['base', 'container']:
                    child_node = build_tree(child, depth + 1)
                    if child_node:
                        if child_node['paramCount'] > 0 or len(child_node['children']) > 0:
                            node['children'].append(child_node)

            return node

        root = op(parent_path)
        if root is None:
            return {'success': False, 'error': f'Path not found: {parent_path}'}

        tree = build_tree(root)
        return {'success': True, 'tree': tree}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def set_parameter(op_path, param_name, value):
    """Set a parameter value."""
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        if not hasattr(op_ref.par, param_name):
            return {'error': f'Parameter not found: {param_name}'}
        setattr(op_ref.par, param_name, value)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def serve_static_file(uri, response):
    """Serve static files from cached assets."""
    static_map = {
        '/ui': 'ui_index',
        '/ui/': 'ui_index',
        '/ui/index.html': 'ui_index',
        '/ui/styles.css': 'ui_styles',
        '/ui/app.js': 'ui_app',
        '/ui/controls.js': 'ui_controls',
        '/ui/preview.js': 'ui_preview',
    }

    dat_name = static_map.get(uri)
    if dat_name and dat_name in _ASSET_CACHE:
        content = _ASSET_CACHE[dat_name]
        ext = '.html'
        for e in MIME_TYPES:
            if uri.endswith(e):
                ext = e
                break
        if uri in ['/ui', '/ui/', '/ui/index.html']:
            ext = '.html'

        response['Content-Type'] = MIME_TYPES.get(ext, 'text/plain')
        response['data'] = content
        return True

    # Try loading from Text DATs as fallback
    try:
        ui_module = op('/project1/mcp_bridge/ui')
        if ui_module and dat_name:
            dat = ui_module.op(dat_name)
            if dat and dat.text:
                ext = '.html'
                for e in MIME_TYPES:
                    if uri.endswith(e):
                        ext = e
                        break
                if uri in ['/ui', '/ui/', '/ui/index.html']:
                    ext = '.html'
                response['Content-Type'] = MIME_TYPES.get(ext, 'text/plain')
                response['data'] = dat.text
                return True
    except:
        pass

    return False


def on_request(uri, method, body, request, response):
    """Handle UI HTTP requests."""
    # Serve static files for /ui routes
    if uri.startswith('/ui') and method == 'GET':
        if serve_static_file(uri, response):
            response['statusCode'] = 200
            response['statusReason'] = 'OK'
            return None  # Response handled directly

    # API endpoints
    if uri == '/ui/schema':
        return scan_custom_parameters(body.get('path', ''))
    elif uri == '/ui/discover':
        return discover_ui_components(
            body.get('path', '/project1'),
            body.get('max_depth', 3)
        )
    elif uri == '/ui/set':
        changes = body.get('changes', [])
        results = []
        for change in changes:
            r = set_parameter(change.get('path', ''), change.get('parameter', ''), change.get('value', ''))
            results.append(r)
        return {'success': True, 'results': results}
    elif uri == '/ui/pulse':
        op_path = body.get('path', '')
        param_name = body.get('parameter', '')
        try:
            op_ref = op(op_path)
            if op_ref and hasattr(op_ref.par, param_name):
                par = getattr(op_ref.par, param_name)
                par.pulse()
                return {'success': True}
            else:
                return {'success': False, 'error': 'Parameter not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    elif uri == '/ui/info':
        try:
            pname = project.name if 'project' in dir() and project else 'Untitled'
            pfolder = project.folder if 'project' in dir() and project else ''
        except Exception:
            pname, pfolder = 'Untitled', ''
        try:
            tdver = app.version if 'app' in dir() else 'unknown'
            tdbuild = app.build if 'app' in dir() else 'unknown'
        except Exception:
            tdver, tdbuild = 'unknown', 'unknown'
        return {
            'projectName': pname,
            'projectPath': pfolder,
            'tdVersion': tdver,
            'tdBuild': tdbuild
        }
    elif uri == '/ui/components/tree':
        return discover_ui_components_hierarchical(
            body.get('path', '/project1'),
            body.get('max_depth', 5)
        )
    elif uri == '/ui/ping' or uri == '/ui/health':
        return {'status': 'ok', 'module': 'ui'}
    else:
        return {'error': f'Unknown UI endpoint: {uri}'}


# === WebSocket handlers ===

def on_websocket_open(webServerDAT, client, uri):
    global _WS_CLIENTS
    client_id = str(id(client))
    _WS_CLIENTS[client_id] = {
        'client': client,
        'subscriptions': [],
        'uri': uri
    }
    webServerDAT.webSocketSendText(client, json.dumps({
        'type': 'connected',
        'message': 'WebSocket connected to TouchDesigner'
    }))


def on_websocket_close(webServerDAT, client):
    global _WS_CLIENTS
    client_id = str(id(client))
    if client_id in _WS_CLIENTS:
        del _WS_CLIENTS[client_id]


def on_websocket_receive(webServerDAT, client, data):
    global _WS_CLIENTS
    client_id = str(id(client))

    try:
        msg = json.loads(data)
        msg_type = msg.get('type', '')

        if msg_type == 'subscribe':
            paths = msg.get('paths', [])
            if client_id in _WS_CLIENTS:
                _WS_CLIENTS[client_id]['subscriptions'] = paths
            webServerDAT.webSocketSendText(client, json.dumps({
                'type': 'subscribed',
                'paths': paths
            }))

        elif msg_type == 'unsubscribe':
            if client_id in _WS_CLIENTS:
                _WS_CLIENTS[client_id]['subscriptions'] = []
            webServerDAT.webSocketSendText(client, json.dumps({
                'type': 'unsubscribed'
            }))

        elif msg_type == 'set':
            path = msg.get('path', '')
            param = msg.get('parameter', '')
            value = msg.get('value', '')
            result = set_parameter(path, param, value)
            webServerDAT.webSocketSendText(client, json.dumps({
                'type': 'set_result',
                **result
            }))
            _broadcast_change(webServerDAT, path, param, value, exclude_client=client_id)

        elif msg_type == 'get_schema':
            path = msg.get('path', '')
            result = scan_custom_parameters(path)
            webServerDAT.webSocketSendText(client, json.dumps({
                'type': 'schema',
                **result
            }))

        elif msg_type == 'ping':
            webServerDAT.webSocketSendText(client, json.dumps({
                'type': 'pong'
            }))

    except Exception as e:
        webServerDAT.webSocketSendText(client, json.dumps({
            'type': 'error',
            'error': str(e)
        }))


def _broadcast_change(webServerDAT, path, param, value, exclude_client=None):
    global _WS_CLIENTS
    message = json.dumps({
        'type': 'change',
        'path': path,
        'parameter': param,
        'value': value
    })

    for client_id, client_info in list(_WS_CLIENTS.items()):
        if client_id == exclude_client:
            continue
        subscriptions = client_info.get('subscriptions', [])
        if not subscriptions or path in subscriptions:
            try:
                webServerDAT.webSocketSendText(client_info['client'], message)
            except:
                if client_id in _WS_CLIENTS:
                    del _WS_CLIENTS[client_id]
