# TouchDesigner MCP Bridge - Server Component
# This script runs INSIDE TouchDesigner to expose an HTTP API
#
# Setup:
# 1. Create a Text DAT and paste this script
# 2. Create a Web Server DAT named 'webserver1'
# 3. Set Web Server DAT port to 9980
# 4. Set Web Server DAT's "DAT" parameter to point to a Text DAT containing the handler code
# 5. Create a CHOP Execute or DAT Execute to initialize on start

import json
import traceback

def get_operator_info(path):
    """Get detailed info about an operator."""
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
            'inputs': [],
            'outputs': []
        }

        # Get all parameters
        for p in op_ref.pars():
            try:
                info['parameters'][p.name] = {
                    'value': str(p.eval()),
                    'default': str(p.default),
                    'mode': str(p.mode),
                    'label': p.label,
                    'page': p.page.name if p.page else None,
                    'readonly': p.readonly,
                    'style': p.style
                }
            except:
                info['parameters'][p.name] = {'error': 'Could not read parameter'}

        # Get inputs
        for i, conn in enumerate(op_ref.inputConnectors):
            info['inputs'].append({
                'index': i,
                'connected': conn.connections is not None and len(conn.connections) > 0
            })

        # Get outputs
        for i, conn in enumerate(op_ref.outputConnectors):
            info['outputs'].append({
                'index': i,
                'connected': conn.connections is not None and len(conn.connections) > 0
            })

        return info
    except Exception as e:
        return {'error': str(e), 'traceback': traceback.format_exc()}


def list_operators(path='/project1'):
    """List all operators under a path."""
    try:
        parent = op(path)
        if parent is None:
            return {'error': f'Path not found: {path}'}

        ops = []
        for child in parent.children:
            ops.append({
                'name': child.name,
                'path': child.path,
                'type': child.type,
                'family': child.family
            })
        return {'operators': ops, 'path': path}
    except Exception as e:
        return {'error': str(e)}


def get_parameter_names(op_type):
    """Get all parameter names for an operator type by creating a temp instance."""
    try:
        # Create a temporary operator to inspect its parameters
        temp_parent = op('/project1')

        # Map type string to operator class
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
            'oscInDAT': oscinDAT,
            'oscinCHOP': oscinCHOP,
            'oscoutDAT': oscoutDAT,
            'datexecDAT': datexecDAT,
            'containerCOMP': containerCOMP,
            'outTOP': outTOP,
            'outCHOP': outCHOP,
        }

        if op_type not in type_map:
            return {'error': f'Unknown operator type: {op_type}', 'available_types': list(type_map.keys())}

        # Create temp operator
        temp = temp_parent.create(type_map[op_type], '__temp_inspect__')

        params = {}
        for p in temp.pars():
            params[p.name] = {
                'label': p.label,
                'default': str(p.default),
                'style': p.style,
                'page': p.page.name if p.page else None
            }

        # Delete temp operator
        temp.destroy()

        return {'type': op_type, 'parameters': params}
    except Exception as e:
        return {'error': str(e), 'traceback': traceback.format_exc()}


def execute_python(code):
    """Execute Python code and return the result."""
    try:
        # Create a dict to capture local variables
        local_vars = {}
        exec(code, globals(), local_vars)

        # Try to get a 'result' variable if set
        if 'result' in local_vars:
            return {'success': True, 'result': str(local_vars['result'])}
        else:
            return {'success': True, 'result': None}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def create_operator(parent_path, op_type, name, parameters=None):
    """Create a new operator."""
    try:
        parent = op(parent_path)
        if parent is None:
            return {'error': f'Parent not found: {parent_path}'}

        # Map type string to operator class
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
            'datexecDAT': datexecDAT,
            'containerCOMP': containerCOMP,
            'baseCOMP': baseCOMP,
            'outTOP': outTOP,
            'outCHOP': outCHOP,
            'textDAT': textDAT,
            'webserverDAT': webserverDAT,
        }

        if op_type not in type_map:
            return {'error': f'Unknown operator type: {op_type}', 'available_types': list(type_map.keys())}

        new_op = parent.create(type_map[op_type], name)

        # Set parameters if provided
        if parameters:
            for param_name, param_value in parameters.items():
                try:
                    if hasattr(new_op.par, param_name):
                        setattr(new_op.par, param_name, param_value)
                except Exception as e:
                    pass  # Skip parameters that fail

        return {'success': True, 'path': new_op.path, 'type': new_op.type}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def set_parameter(op_path, param_name, value):
    """Set a parameter value on an operator."""
    try:
        op_ref = op(op_path)
        if op_ref is None:
            return {'error': f'Operator not found: {op_path}'}

        if not hasattr(op_ref.par, param_name):
            return {'error': f'Parameter not found: {param_name}'}

        setattr(op_ref.par, param_name, value)
        return {'success': True, 'path': op_path, 'parameter': param_name, 'value': str(getattr(op_ref.par, param_name).eval())}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def connect_operators(from_path, to_path, from_index=0, to_index=0):
    """Connect two operators."""
    try:
        from_op = op(from_path)
        to_op = op(to_path)

        if from_op is None:
            return {'error': f'Source operator not found: {from_path}'}
        if to_op is None:
            return {'error': f'Target operator not found: {to_path}'}

        to_op.inputConnectors[to_index].connect(from_op.outputConnectors[from_index])
        return {'success': True, 'from': from_path, 'to': to_path}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def delete_operator(op_path):
    """Delete an operator."""
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
    """Disconnect an input on an operator."""
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


# HTTP Request Handler for Web Server DAT
def onHTTPRequest(webServerDAT, request, response):
    """Handle incoming HTTP requests."""

    path = request['uri']
    method = request['method']

    # Parse JSON body if present (TouchDesigner uses 'data' key for POST body)
    body = {}
    if request.get('data'):
        raw = request['data']
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        body = json.loads(raw)

    result = {'error': 'Unknown endpoint'}

    # Route requests
    if path == '/ping':
        result = {'status': 'ok', 'message': 'TouchDesigner MCP Bridge is running'}

    elif path == '/operators' or path.startswith('/operators?'):
        parent_path = body.get('path', request.get('pars', {}).get('path', '/'))
        result = list_operators(parent_path)

    elif path == '/operator/info':
        op_path = body.get('path', request.get('pars', {}).get('path', ''))
        result = get_operator_info(op_path)

    elif path == '/operator/parameters':
        op_type = body.get('type', request.get('pars', {}).get('type', ''))
        result = get_parameter_names(op_type)

    elif path == '/execute':
        code = body.get('code', '')
        result = execute_python(code)

    elif path == '/create':
        result = create_operator(
            body.get('parent', '/'),
            body.get('type', ''),
            body.get('name', ''),
            body.get('parameters', {})
        )

    elif path == '/set':
        result = set_parameter(
            body.get('path', ''),
            body.get('parameter', ''),
            body.get('value', '')
        )

    elif path == '/connect':
        result = connect_operators(
            body.get('from', ''),
            body.get('to', ''),
            body.get('from_index', 0),
            body.get('to_index', 0)
        )

    elif path == '/delete':
        result = delete_operator(body.get('path', ''))

    elif path == '/disconnect':
        result = disconnect_operator(
            body.get('path', ''),
            body.get('input_index', 0)
        )

    # Send response
    response['statusCode'] = 200
    response['statusReason'] = 'OK'
    response['data'] = json.dumps(result, indent=2)

    return response


# For testing directly in TouchDesigner
if __name__ == '__main__':
    print("TouchDesigner MCP Bridge Server")
    print("Available functions:")
    print("  - list_operators(path)")
    print("  - get_operator_info(path)")
    print("  - get_parameter_names(op_type)")
    print("  - execute_python(code)")
    print("  - create_operator(parent, type, name, params)")
    print("  - set_parameter(path, param, value)")
    print("  - connect_operators(from, to)")
