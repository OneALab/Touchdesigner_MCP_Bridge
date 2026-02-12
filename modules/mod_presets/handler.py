# Preset Module Handler
# Save/load/delete parameter presets for COMPs
import json
import traceback


def setup(bridge_op):
    """Create preset storage table in the bridge."""
    existing = bridge_op.op('preset_storage')
    if existing is None:
        preset_table = bridge_op.create(tableDAT, 'preset_storage')
        preset_table.nodeX = 400
        preset_table.nodeY = 0
        preset_table.clear()
        preset_table.appendRow(['name', 'comp_path', 'data', 'created', 'modified'])
        print("    Created preset_storage table")


def _get_table():
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        return None
    return bridge.op('preset_storage')


def list_presets(comp_path=None):
    try:
        table = _get_table()
        if table is None:
            return {'success': False, 'error': 'Preset table not available'}

        presets = []
        for i in range(1, table.numRows):
            row = table.row(i)
            name = str(row[0])
            path = str(row[1])
            created = str(row[3]) if len(row) > 3 else ''
            modified = str(row[4]) if len(row) > 4 else ''

            if comp_path and path != comp_path:
                continue

            presets.append({
                'name': name,
                'comp_path': path,
                'created': created,
                'modified': modified
            })

        return {'success': True, 'presets': presets, 'count': len(presets)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def save_preset(name, comp_path):
    try:
        if not name:
            return {'success': False, 'error': 'Preset name required'}

        comp = op(comp_path)
        if comp is None:
            return {'success': False, 'error': f'Component not found: {comp_path}'}
        if comp.family != 'COMP':
            return {'success': False, 'error': f'Not a COMP: {comp_path}'}

        param_data = {}
        for page in comp.customPages:
            for par in page.pars:
                if par.isCustom and not par.readOnly:
                    if par.isMenu:
                        param_data[par.name] = par.menuIndex
                    elif par.isToggle:
                        param_data[par.name] = int(par.eval())
                    else:
                        param_data[par.name] = par.eval()

        data_str = json.dumps(param_data)

        import datetime
        now = datetime.datetime.now().isoformat()

        table = _get_table()
        if table is None:
            return {'success': False, 'error': 'Preset table not available'}

        existing_row = None
        for i in range(1, table.numRows):
            if str(table[i, 0]) == name and str(table[i, 1]) == comp_path:
                existing_row = i
                break

        if existing_row:
            table[existing_row, 2] = data_str
            table[existing_row, 4] = now
        else:
            table.appendRow([name, comp_path, data_str, now, now])

        return {
            'success': True,
            'name': name,
            'comp_path': comp_path,
            'paramCount': len(param_data)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def load_preset(name, comp_path):
    try:
        table = _get_table()
        if table is None:
            return {'success': False, 'error': 'Preset table not available'}

        preset_row = None
        for i in range(1, table.numRows):
            if str(table[i, 0]) == name and str(table[i, 1]) == comp_path:
                preset_row = i
                break

        if preset_row is None:
            return {'success': False, 'error': f'Preset not found: {name}'}

        data_str = str(table[preset_row, 2])
        param_data = json.loads(data_str)

        comp = op(comp_path)
        if comp is None:
            return {'success': False, 'error': f'Component not found: {comp_path}'}

        applied = []
        errors = []
        for param_name, value in param_data.items():
            try:
                par = getattr(comp.par, param_name, None)
                if par is not None and not par.readOnly:
                    if par.isMenu:
                        par.menuIndex = int(value)
                    elif par.isToggle:
                        par.val = bool(int(value))
                    else:
                        par.val = value
                    applied.append(param_name)
            except Exception as pe:
                errors.append(f'{param_name}: {str(pe)}')

        return {
            'success': True,
            'name': name,
            'applied': applied,
            'appliedCount': len(applied),
            'errors': errors if errors else None
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def delete_preset(name, comp_path):
    try:
        table = _get_table()
        if table is None:
            return {'success': False, 'error': 'Preset table not available'}

        for i in range(1, table.numRows):
            if str(table[i, 0]) == name and str(table[i, 1]) == comp_path:
                table.deleteRow(i)
                return {'success': True, 'name': name, 'deleted': True}

        return {'success': False, 'error': f'Preset not found: {name}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def on_request(uri, method, body, request, response):
    """Handle preset HTTP requests."""
    if uri == '/presets/list':
        return list_presets(body.get('comp_path'))
    elif uri == '/presets/save':
        return save_preset(body.get('name', ''), body.get('comp_path', ''))
    elif uri == '/presets/load':
        return load_preset(body.get('name', ''), body.get('comp_path', ''))
    elif uri == '/presets/delete':
        return delete_preset(body.get('name', ''), body.get('comp_path', ''))
    else:
        return {'error': f'Unknown preset endpoint: {uri}'}
