# TouchDesigner MCP Bridge - Setup Script
# Run this script ONCE inside TouchDesigner to set up the HTTP bridge
#
# Usage:
# 1. Open TouchDesigner
# 2. Create a Text DAT, paste this script
# 3. Run it once to create the Web Server

import json
import traceback

def setup_bridge():
    """Set up the MCP bridge web server in TouchDesigner."""

    project = op('/project1')
    if project is None:
        print("ERROR: /project1 not found. Are you in a standard TouchDesigner project?")
        return

    # Delete existing bridge if present
    existing = op('/project1/mcp_bridge')
    if existing:
        existing.destroy()
        print("Deleted existing MCP Bridge, recreating...")

    # Create container for bridge
    bridge = project.create(baseCOMP, 'mcp_bridge')
    bridge.nodeX = -400
    bridge.nodeY = 400

    # Create Web Server DAT
    webserver = bridge.create(webserverDAT, 'webserver')
    webserver.par.port = 9980
    webserver.par.active = True
    webserver.nodeX = 0
    webserver.nodeY = 0

    # Create handler Text DAT
    handler = bridge.create(textDAT, 'handler')
    handler.nodeX = 0
    handler.nodeY = -150

    # Set the handler code - FIXED version with proper body parsing
    handler_code = '''# MCP Bridge HTTP Handler - Fixed Version
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
        body = json.loads(raw)
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
        # Use TD globals so operator classes are available
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
            return {'success': True, 'disconnected': op_path, 'input': input_index}
        else:
            return {'success': True, 'message': 'No connection to disconnect'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

# === Text DAT Tools ===

def get_text_dat(op_path):
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        if op_ref.family != 'DAT':
            return {'error': f'Not a DAT: {op_path}'}
        return {'success': True, 'path': op_path, 'text': op_ref.text}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def set_text_dat(op_path, content):
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        if op_ref.family != 'DAT':
            return {'error': f'Not a DAT: {op_path}'}
        op_ref.text = content
        return {'success': True, 'path': op_path, 'length': len(content)}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def run_text_script(op_path):
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        if op_ref.family != 'DAT':
            return {'error': f'Not a DAT: {op_path}'}
        op_ref.run()
        return {'success': True, 'ran': op_path}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

# === Extension Tools ===

def get_extension(comp_path):
    try:
        comp = op(comp_path)
        if comp is None:
            return {'error': f'Operator not found: {comp_path}'}
        if comp.family != 'COMP':
            return {'error': f'Not a COMP: {comp_path}'}

        ext_dat = comp.op('extText') or comp.op('ext1')
        if ext_dat:
            return {
                'success': True,
                'path': comp_path,
                'extension_dat': ext_dat.path,
                'code': ext_dat.text,
                'has_extension': hasattr(comp, 'ext')
            }
        return {'success': True, 'path': comp_path, 'has_extension': False, 'code': None}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def set_extension(comp_path, code, ext_name='Ext'):
    try:
        comp = op(comp_path)
        if comp is None:
            return {'error': f'Operator not found: {comp_path}'}
        if comp.family != 'COMP':
            return {'error': f'Not a COMP: {comp_path}'}

        ext_dat = comp.op('extText')
        if not ext_dat:
            ext_dat = comp.create(textDAT, 'extText')
            ext_dat.nodeX = -200
            ext_dat.nodeY = -200
            comp.par.extension1 = 'extText'
            comp.par.promoteextension1 = True

        ext_dat.text = code
        comp.par.reinitextensions.pulse()
        return {'success': True, 'path': comp_path, 'extension_dat': ext_dat.path}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def create_extension(comp_path, class_name='Ext', methods=None):
    try:
        comp = op(comp_path)
        if comp is None:
            return {'error': f'Operator not found: {comp_path}'}
        if comp.family != 'COMP':
            return {'error': f'Not a COMP: {comp_path}'}

        methods = methods or []
        method_stubs = ''
        for m in methods:
            method_stubs += "\\n    def " + m + "(self):\\n        pass\\n"

        code = "class " + class_name + ":\\n    def __init__(self, ownerComp):\\n        self.ownerComp = ownerComp\\n" + method_stubs
        return set_extension(comp_path, code, class_name)
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def promote_parameter(comp_path, param_name, label=None, page='Custom'):
    try:
        comp = op(comp_path)
        if comp is None:
            return {'error': f'Operator not found: {comp_path}'}
        if comp.family != 'COMP':
            return {'error': f'Not a COMP: {comp_path}'}

        pg = comp.appendCustomPage(page)
        par = pg.appendStr(param_name, label=label or param_name)
        return {'success': True, 'path': comp_path, 'parameter': param_name, 'page': page}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

# === Package Management Tools ===

def pip_install(package):
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return {'success': True, 'package': package, 'output': result.stdout}
        else:
            return {'success': False, 'package': package, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def pip_list():
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            return {'success': True, 'packages': packages}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def import_check(module_name):
    try:
        exec(f'import {module_name}')
        mod = eval(module_name)
        version = getattr(mod, '__version__', 'unknown')
        return {'success': True, 'module': module_name, 'importable': True, 'version': version}
    except ImportError as e:
        return {'success': True, 'module': module_name, 'importable': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

# === Debugging Tools ===

def get_errors():
    try:
        textport = op('/textport')
        if textport:
            return {'success': True, 'errors': textport.text[-5000:]}
        return {'success': True, 'errors': 'Textport not accessible'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_cook_time(op_path):
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}
        return {
            'success': True,
            'path': op_path,
            'cookTime': op_ref.cookTime,
            'cookFrame': op_ref.cookFrame,
            'cookAbsFrame': op_ref.cookAbsFrame,
            'cpuMemory': op_ref.cpuMemory if hasattr(op_ref, 'cpuMemory') else None,
            'gpuMemory': op_ref.gpuMemory if hasattr(op_ref, 'gpuMemory') else None
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def find_operators(pattern='*', op_type=None, parent_path='/project1'):
    try:
        parent_op = op(parent_path)
        if parent_op is None:
            return {'error': f'Parent not found: {parent_path}'}

        found = []
        for child in parent_op.findChildren(name=pattern, maxDepth=10):
            if op_type is None or child.type == op_type or child.OPType == op_type:
                found.append({
                    'name': child.name,
                    'path': child.path,
                    'type': child.type,
                    'family': child.family
                })
        return {'success': True, 'count': len(found), 'operators': found}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def onHTTPRequest(webServerDAT, request, response):
    uri = request['uri']
    body = parse_body(request)

    result = {'error': 'Unknown endpoint'}

    if uri == '/ping':
        result = {'status': 'ok', 'message': 'TouchDesigner MCP Bridge running'}
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
    # Text DAT endpoints
    elif uri == '/text/get':
        result = get_text_dat(body.get('path', ''))
    elif uri == '/text/set':
        result = set_text_dat(body.get('path', ''), body.get('content', ''))
    elif uri == '/text/run':
        result = run_text_script(body.get('path', ''))
    # Extension endpoints
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
    # Package management endpoints
    elif uri == '/pip/install':
        result = pip_install(body.get('package', ''))
    elif uri == '/pip/list':
        result = pip_list()
    elif uri == '/pip/check':
        result = import_check(body.get('module', ''))
    # Debug endpoints
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

    response['statusCode'] = 200
    response['statusReason'] = 'OK'
    response['data'] = json.dumps(result, indent=2)
    return response
'''

    handler.text = handler_code

    # Point webserver to handler
    webserver.par.callbacks = 'handler'

    print("=" * 50)
    print("MCP Bridge created successfully!")
    print("=" * 50)
    print(f"Web Server running on port 9980")
    print(f"Test with: http://127.0.0.1:9980/ping")
    print("")
    print("The bridge is at /project1/mcp_bridge")
    print("Save your project to keep the bridge.")
    print("=" * 50)


# Run setup
setup_bridge()
