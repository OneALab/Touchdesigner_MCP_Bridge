# TouchDesigner MCP Bridge - Core Setup Script
# Creates the base bridge with MCP/Claude Code essential endpoints
#
# For modules (UI, presets, cues, StreamDeck, etc.), run module_loader.py after this.
#
# Usage:
# 1. Open TouchDesigner
# 2. Create a Text DAT, paste this script
# 3. Run it once to create the Web Server
# 4. Then run module_loader.py to load modules

import json
import traceback

def setup_bridge():
    """Set up the MCP bridge web server in TouchDesigner.

    Non-destructive: preserves existing bridge and module data (presets,
    cues, StreamDeck config, etc.) when re-run.  Only the core handler
    code and webserver settings are updated.
    """

    project = op('/project1')
    if project is None:
        print("ERROR: /project1 not found. Are you in a standard TouchDesigner project?")
        return

    # Create or reuse bridge container
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        bridge = project.create(baseCOMP, 'mcp_bridge')
        bridge.nodeX = -400
        bridge.nodeY = 400
        print("Created new MCP Bridge container")
    else:
        print("Updating existing MCP Bridge (data preserved)")

    # Create or reuse Web Server DAT
    webserver = bridge.op('webserver')
    if webserver is None:
        webserver = bridge.create(webserverDAT, 'webserver')
        webserver.nodeX = 0
        webserver.nodeY = 0
    webserver.par.port = 9980
    webserver.par.active = True

    # Create or reuse handler Text DAT
    handler = bridge.op('handler')
    if handler is None:
        handler = bridge.create(textDAT, 'handler')
        handler.nodeX = 0
        handler.nodeY = -150

    # Create module registry table if it doesn't exist
    registry = bridge.op('module_registry')
    if registry is None:
        registry = bridge.create(tableDAT, 'module_registry')
        registry.nodeX = -200
        registry.nodeY = -150
        registry.clear()
        registry.appendRow(['name', 'version', 'prefix', 'status', 'loaded_at', 'description'])

    # Set the handler code - Core MCP endpoints only
    handler_code = '''# MCP Bridge HTTP Handler - Core Endpoints
# For module endpoints (UI, presets, cues, etc.), see port 9981
import json
import traceback

# Store TD globals at module load time
_TD_GLOBALS = {
    'containerCOMP': containerCOMP,
    'baseCOMP': baseCOMP,
    'timerCHOP': timerCHOP,
    'moviefileinTOP': moviefileinTOP,
    'constantTOP': constantTOP,
    'switchTOP': switchTOP,
    'nullTOP': nullTOP,
    'infoCHOP': infoCHOP,
    'selectCHOP': selectCHOP,
    'mergeCHOP': mergeCHOP,
    'mathCHOP': mathCHOP,
    'renameCHOP': renameCHOP,
    'scriptCHOP': scriptCHOP,
    'oscinDAT': oscinDAT,
    'oscinCHOP': oscinCHOP,
    'oscoutDAT': oscoutDAT,
    'textDAT': textDAT,
    'outTOP': outTOP,
    'outCHOP': outCHOP,
    'nullCHOP': nullCHOP,
    'op': op,
    'parent': parent,
    'me': me,
    'mod': mod,
    'ext': ext,
    'ParMode': ParMode,
}

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

def get_operator_info(path):
    try:
        op_ref = op(path)
        if op_ref is None:
            return {'error': f'Operator not found: {path}'}
        info = {
            'path': op_ref.path,
            'name': op_ref.name,
            'type': op_ref.type,
            'family': op_ref.family,
            'parameters': {},
        }
        for p in op_ref.pars():
            try:
                info['parameters'][p.name] = {
                    'value': str(p.eval()),
                    'default': str(p.default),
                    'label': p.label,
                    'style': p.style
                }
            except:
                pass
        return info
    except Exception as e:
        return {'error': str(e), 'traceback': traceback.format_exc()}

def list_operators(path='/project1'):
    try:
        parent_op = op(path)
        if parent_op is None:
            return {'error': f'Path not found: {path}'}
        ops = []
        for child in parent_op.children:
            ops.append({
                'name': child.name,
                'path': child.path,
                'type': child.type,
                'family': child.family
            })
        return {'operators': ops, 'path': path}
    except Exception as e:
        return {'error': str(e)}

def execute_python(code):
    try:
        exec_globals = dict(_TD_GLOBALS)
        exec_globals['__builtins__'] = __builtins__
        local_vars = {}
        exec(code, exec_globals, local_vars)
        if 'result' in local_vars:
            return {'success': True, 'result': str(local_vars['result'])}
        return {'success': True, 'result': None}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def create_operator(parent_path, op_type, name, parameters=None):
    try:
        parent_op = op(parent_path)
        if parent_op is None:
            return {'error': f'Parent not found: {parent_path}'}

        type_map = {
            'timerCHOP': timerCHOP,
            'moviefileinTOP': moviefileinTOP,
            'constantTOP': constantTOP,
            'switchTOP': switchTOP,
            'nullTOP': nullTOP,
            'infoCHOP': infoCHOP,
            'selectCHOP': selectCHOP,
            'mergeCHOP': mergeCHOP,
            'mathCHOP': mathCHOP,
            'renameCHOP': renameCHOP,
            'scriptCHOP': scriptCHOP,
            'oscinDAT': oscinDAT,
            'oscinCHOP': oscinCHOP,
            'oscoutDAT': oscoutDAT,
            'containerCOMP': containerCOMP,
            'baseCOMP': baseCOMP,
            'outTOP': outTOP,
            'outCHOP': outCHOP,
            'textDAT': textDAT,
            'nullCHOP': nullCHOP,
        }

        if op_type not in type_map:
            return {'error': f'Unknown type: {op_type}', 'available': list(type_map.keys())}

        new_op = parent_op.create(type_map[op_type], name)
        if parameters:
            for pname, pval in parameters.items():
                try:
                    if hasattr(new_op.par, pname):
                        setattr(new_op.par, pname, pval)
                except:
                    pass
        return {'success': True, 'path': new_op.path}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def set_parameter(op_path, param_name, value):
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

def connect_operators(from_path, to_path, from_index=0, to_index=0):
    try:
        from_op = op(from_path)
        to_op = op(to_path)
        if from_op is None:
            return {'error': f'Source not found: {from_path}'}
        if to_op is None:
            return {'error': f'Target not found: {to_path}'}
        to_op.inputConnectors[to_index].connect(from_op)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def delete_operator(op_path):
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        name = op_ref.name
        op_ref.destroy()
        return {'success': True, 'deleted': name}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def disconnect_operator(op_path, input_index=0):
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        connector = op_ref.inputConnectors[input_index]
        if connector.connections:
            connector.disconnect()
            return {'success': True}
        return {'success': True, 'message': 'No connection to disconnect'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def get_text_dat(path):
    try:
        text_op = op(path)
        if text_op is None:
            return {'error': f'Operator not found: {path}'}
        if not hasattr(text_op, 'text'):
            return {'error': f'Not a text DAT: {path}'}
        return {'success': True, 'content': text_op.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def set_text_dat(path, content):
    try:
        text_op = op(path)
        if text_op is None:
            return {'error': f'Operator not found: {path}'}
        if not hasattr(text_op, 'text'):
            return {'error': f'Not a text DAT: {path}'}
        text_op.text = content
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def run_text_script(path):
    try:
        text_op = op(path)
        if text_op is None:
            return {'error': f'Operator not found: {path}'}
        text_op.run()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def get_extension(path):
    try:
        comp = op(path)
        if comp is None:
            return {'error': f'Operator not found: {path}'}
        ext_dat = comp.op('Ext') or comp.op('ext')
        if ext_dat is None:
            return {'success': True, 'code': None, 'message': 'No extension found'}
        return {'success': True, 'code': ext_dat.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def set_extension(path, code, name='Ext'):
    try:
        comp = op(path)
        if comp is None:
            return {'error': f'Operator not found: {path}'}
        ext_dat = comp.op(name)
        if ext_dat is None:
            ext_dat = comp.create(textDAT, name)
        ext_dat.text = code
        comp.par.extension1 = name
        comp.par.promoteextension1 = True
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def create_extension(path, class_name='Ext', methods=None):
    try:
        comp = op(path)
        if comp is None:
            return {'error': f'Operator not found: {path}'}
        methods = methods or []
        method_code = ""
        for m in methods:
            method_code += f"\\n    def {m}(self):\\n        pass\\n"
        code = f"""class {class_name}:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
{method_code}
"""
        return set_extension(path, code, class_name)
    except Exception as e:
        return {'success': False, 'error': str(e)}

def promote_parameter(path, param_name, label=None, page='Custom'):
    try:
        comp = op(path)
        if comp is None:
            return {'error': f'Operator not found: {path}'}
        custom_page = comp.customPages[0] if comp.customPages else comp.appendCustomPage(page)
        par = custom_page.appendFloat(param_name, label=label or param_name)
        return {'success': True, 'parameter': param_name}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def pip_install(package):
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package],
            capture_output=True, text=True
        )
        return {'success': result.returncode == 0, 'output': result.stdout, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def pip_list():
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True, text=True
        )
        packages = json.loads(result.stdout) if result.returncode == 0 else []
        return {'success': True, 'packages': packages}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def import_check(module_name):
    try:
        __import__(module_name)
        return {'success': True, 'available': True}
    except ImportError:
        return {'success': True, 'available': False}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_errors():
    try:
        errors = []
        return {'success': True, 'errors': errors, 'count': len(errors)}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_cook_time(path):
    try:
        op_ref = op(path)
        if op_ref is None:
            return {'error': f'Operator not found: {path}'}
        return {
            'success': True,
            'path': path,
            'cookTime': op_ref.cookTime,
            'cookFrame': op_ref.cookFrame
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def find_operators(pattern='*', op_type=None, parent_path='/project1'):
    try:
        parent_op = op(parent_path)
        if parent_op is None:
            return {'error': f'Parent not found: {parent_path}'}
        found = []
        for child in parent_op.findChildren(name=pattern, maxDepth=10):
            if op_type and child.type != op_type:
                continue
            found.append({
                'name': child.name,
                'path': child.path,
                'type': child.type,
                'family': child.family
            })
        return {'success': True, 'count': len(found), 'operators': found}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def get_loaded_modules():
    """List loaded modules from the registry."""
    try:
        bridge = op('/project1/mcp_bridge')
        registry = bridge.op('module_registry') if bridge else None
        if registry is None:
            return {'success': True, 'modules': [], 'count': 0}

        modules = []
        for i in range(1, registry.numRows):
            row = registry.row(i)
            modules.append({
                'name': str(row[0]),
                'version': str(row[1]),
                'prefix': str(row[2]),
                'status': str(row[3]),
                'loaded_at': str(row[4]),
                'description': str(row[5]) if len(row) > 5 else ''
            })
        return {'success': True, 'modules': modules, 'count': len(modules)}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def onHTTPRequest(webServerDAT, request, response):
    uri = request['uri']
    method = request.get('method', 'GET')
    body = parse_body(request)

    result = {'error': 'Unknown endpoint'}

    # Core MCP endpoints
    if uri == '/ping':
        modules = get_loaded_modules()
        result = {
            'status': 'ok',
            'service': 'core',
            'port': 9980,
            'message': 'TouchDesigner MCP Bridge running',
            'modules_port': 9981,
            'modules': modules.get('modules', [])
        }
    elif uri == '/modules':
        result = get_loaded_modules()
    elif uri == '/operators':
        result = list_operators(body.get('path', '/project1'))
    elif uri == '/operator/info':
        result = get_operator_info(body.get('path', ''))
    elif uri == '/execute':
        result = execute_python(body.get('code', ''))
    elif uri == '/create':
        result = create_operator(
            body.get('parent', '/project1'),
            body.get('type', ''),
            body.get('name', ''),
            body.get('parameters', {})
        )
    elif uri == '/set':
        result = set_parameter(
            body.get('path', ''),
            body.get('parameter', ''),
            body.get('value', '')
        )
    elif uri == '/connect':
        result = connect_operators(
            body.get('from', ''),
            body.get('to', ''),
            body.get('from_index', 0),
            body.get('to_index', 0)
        )
    elif uri == '/delete':
        result = delete_operator(body.get('path', ''))
    elif uri == '/disconnect':
        result = disconnect_operator(
            body.get('path', ''),
            body.get('input_index', 0)
        )
    elif uri == '/text/get':
        result = get_text_dat(body.get('path', ''))
    elif uri == '/text/set':
        result = set_text_dat(body.get('path', ''), body.get('content', ''))
    elif uri == '/text/run':
        result = run_text_script(body.get('path', ''))
    elif uri == '/extension/get':
        result = get_extension(body.get('path', ''))
    elif uri == '/extension/set':
        result = set_extension(
            body.get('path', ''),
            body.get('code', ''),
            body.get('name', 'Ext')
        )
    elif uri == '/extension/create':
        result = create_extension(
            body.get('path', ''),
            body.get('class_name', 'Ext'),
            body.get('methods', [])
        )
    elif uri == '/extension/promote':
        result = promote_parameter(
            body.get('path', ''),
            body.get('param_name', ''),
            body.get('label'),
            body.get('page', 'Custom')
        )
    elif uri == '/pip/install':
        result = pip_install(body.get('package', ''))
    elif uri == '/pip/list':
        result = pip_list()
    elif uri == '/pip/check':
        result = import_check(body.get('module', ''))
    elif uri == '/debug/errors':
        result = get_errors()
    elif uri == '/debug/cooktime':
        result = get_cook_time(body.get('path', ''))
    elif uri == '/find':
        result = find_operators(
            body.get('pattern', '*'),
            body.get('op_type'),
            body.get('parent', '/project1')
        )
    else:
        result = {'error': f'Unknown endpoint: {uri}. Module endpoints available on port 9981.'}

    response['statusCode'] = 200
    response['statusReason'] = 'OK'
    response['data'] = json.dumps(result, indent=2)
    return response
'''

    handler.text = handler_code

    # Point webserver to handler
    webserver.par.callbacks = 'handler'

    print("=" * 50)
    print("MCP Bridge (Core) created successfully!")
    print("=" * 50)
    print("Core API: http://127.0.0.1:9980/ping")
    print("Core endpoints: /ping, /modules, /operators, /execute, /create, etc.")
    print("")
    print("Next: Run module_loader.py to load modules (UI, cues, presets, etc.)")
    print("The bridge is at /project1/mcp_bridge")
    print("Save your project to keep the bridge.")
    print("=" * 50)


# Run setup
setup_bridge()
