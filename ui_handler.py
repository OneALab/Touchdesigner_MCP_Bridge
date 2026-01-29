# UI Module Handler - handles /ui, /presets, /cues, /preview endpoints
import json
import traceback

# MIME types for static file serving
MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
}

# Global cue state
_cue_state = {
    'current_index': 0,
    'autofollow_timer': None
}

# WebSocket clients
_WS_CLIENTS = {}

def parse_body(request):
    """Parse request body from POST data."""
    body = {}
    if request.get('data'):
        raw = request['data']
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        body = json.loads(raw)
    return body

# === Web UI Functions ===

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
            """Get count of custom parameters in a comp."""
            count = 0
            for page in comp.customPages:
                count += len(page.pars)
            return count

        def get_custom_params_list(comp):
            """Get list of custom parameter info."""
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
            """Recursively build tree of components."""
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

            # Find direct children that are baseCOMP or containerCOMP
            for child in comp.children:
                if child.family == 'COMP' and child.type in ['baseCOMP', 'containerCOMP']:
                    child_node = build_tree(child, depth + 1)
                    if child_node:
                        # Include if it has params or has children with params
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
    """Serve static files from Text DATs in the ui module."""
    try:
        ui_module = me.parent()

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
        if dat_name:
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
        return False
    except:
        return False

# === Preview Functions ===

def get_top_preview(op_path, width=160, height=120, quality=80):
    """Return image bytes of a TOP for thumbnail preview."""
    try:
        top = op(op_path)
        if top is None:
            return {'error': f'Operator not found: {op_path}'}
        if top.family != 'TOP':
            return {'error': f'Not a TOP: {op_path} is {top.family}'}

        if top.width == 0 or top.height == 0:
            return {'error': f'TOP has no resolution: {op_path}'}

        top.cook(force=True)

        image_bytes = None
        errors = []

        try:
            image_bytes = top.saveByteArray('.png')
        except Exception as e1:
            errors.append(f'PNG: {e1}')

        if image_bytes is None or len(image_bytes) == 0:
            try:
                image_bytes = top.saveByteArray('.jpg', quality)
            except Exception as e2:
                errors.append(f'JPG: {e2}')

        if image_bytes is None or len(image_bytes) == 0:
            try:
                image_bytes = top.saveByteArray('.jpg')
            except Exception as e3:
                errors.append(f'JPG: {e3}')

        if image_bytes is None or len(image_bytes) == 0:
            return {'error': f'All methods failed: {"; ".join(errors)}'}

        return image_bytes
    except Exception as e:
        return {'error': f'{type(e).__name__}: {str(e)}'}

def get_chop_preview(op_path, max_samples=100):
    """Return downsampled CHOP channel data for graphing."""
    try:
        chop = op(op_path)
        if chop is None:
            return {'error': f'Operator not found: {op_path}'}
        if chop.family != 'CHOP':
            return {'error': f'Not a CHOP: {op_path} is {chop.family}'}

        data = {
            'success': True,
            'path': op_path,
            'numSamples': getattr(chop, 'numSamples', 0),
            'sampleRate': getattr(chop, 'sampleRate', 0),
            'channels': []
        }

        for chan in chop.chans():
            try:
                vals = list(chan.vals)
                if not vals:
                    continue
                if len(vals) > max_samples and max_samples > 0:
                    step = max(1, len(vals) // max_samples)
                    vals = vals[::step][:max_samples]
                chan_min = min(vals)
                chan_max = max(vals)
                data['channels'].append({
                    'name': chan.name,
                    'values': vals,
                    'min': chan_min,
                    'max': chan_max
                })
            except Exception:
                continue

        return data
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def discover_previews(parent_path='/project1', max_depth=1, include_nested=False):
    """Find TOPs and CHOPs that can be previewed."""
    try:
        parent_op = op(parent_path)
        if parent_op is None:
            return {'error': f'Path not found: {parent_path}'}

        tops = []
        chops = []

        def get_parent_path(operator):
            parent = operator.parent()
            if parent and parent.path != parent_path:
                return parent.name
            return None

        def should_include(operator):
            if include_nested:
                return True
            parent = operator.parent()
            while parent and parent.path != parent_path:
                if parent.type == 'baseCOMP':
                    return False
                parent = parent.parent()
            return True

        for t in parent_op.findChildren(maxDepth=max_depth):
            if not should_include(t):
                continue
            parent_name = get_parent_path(t)
            if t.family == 'TOP':
                if t.width == 0 or t.height == 0:
                    continue
                tops.append({
                    'path': t.path,
                    'name': t.name,
                    'type': t.type,
                    'parent': parent_name,
                    'width': t.width,
                    'height': t.height
                })
            elif t.family == 'CHOP':
                if t.numChans == 0:
                    continue
                chops.append({
                    'path': t.path,
                    'name': t.name,
                    'type': t.type,
                    'parent': parent_name,
                    'numChannels': t.numChans,
                    'numSamples': t.numSamples
                })

        return {
            'success': True,
            'tops': tops,
            'chops': chops,
            'topCount': len(tops),
            'chopCount': len(chops)
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

# === Preset Functions ===

def get_preset_table():
    """Get or create the preset storage table."""
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        return None

    preset_table = bridge.op('preset_storage')
    if preset_table is None:
        preset_table = bridge.create(tableDAT, 'preset_storage')
        preset_table.nodeX = 400
        preset_table.nodeY = 0
        preset_table.clear()
        preset_table.appendRow(['name', 'comp_path', 'data', 'created', 'modified'])
    return preset_table

def list_presets(comp_path=None):
    """List all saved presets."""
    try:
        table = get_preset_table()
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
    """Save current parameter values as a preset."""
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

        table = get_preset_table()
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
    """Load a preset and apply values to component."""
    try:
        table = get_preset_table()
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
    """Delete a preset."""
    try:
        table = get_preset_table()
        if table is None:
            return {'success': False, 'error': 'Preset table not available'}

        for i in range(1, table.numRows):
            if str(table[i, 0]) == name and str(table[i, 1]) == comp_path:
                table.deleteRow(i)
                return {'success': True, 'name': name, 'deleted': True}

        return {'success': False, 'error': f'Preset not found: {name}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# === Cue Functions ===

def get_cue_table():
    """Get or create the cue storage table."""
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        return None

    cue_table = bridge.op('cue_storage')
    if cue_table is None:
        cue_table = bridge.create(tableDAT, 'cue_storage')
        cue_table.nodeX = 400
        cue_table.nodeY = -100
        cue_table.clear()
        cue_table.appendRow(['id', 'index', 'name', 'snapshot', 'duration', 'autofollow', 'actions', 'created', 'modified'])
    return cue_table

def snapshot_all_components(parent_path='/project1', max_depth=3):
    """Capture current parameter values from all COMPs with custom parameters."""
    try:
        parent = op(parent_path)
        if parent is None:
            return {'success': False, 'error': f'Parent not found: {parent_path}'}

        snapshot = {}
        comps = parent.findChildren(type=COMP, maxDepth=max_depth)

        for comp in comps:
            if 'mcp_bridge' in comp.path:
                continue

            custom_params = {}
            has_custom = False

            for page in comp.customPages:
                for par in page.pars:
                    if par.isCustom and not par.readOnly:
                        has_custom = True
                        if par.isMenu:
                            custom_params[par.name] = par.menuIndex
                        elif par.isToggle:
                            custom_params[par.name] = int(par.eval())
                        else:
                            custom_params[par.name] = par.eval()

            if has_custom:
                snapshot[comp.path] = {
                    'enabled': True,
                    'name': comp.name,
                    'params': custom_params,
                    'param_count': len(custom_params)
                }

        return {
            'success': True,
            'snapshot': snapshot,
            'component_count': len(snapshot)
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def list_cues():
    """List all cues in order."""
    global _cue_state
    try:
        table = get_cue_table()
        if table is None:
            return {'success': False, 'error': 'Cue table not available'}

        cues = []
        for i in range(1, table.numRows):
            row = table.row(i)

            snapshot = {}
            if row[3]:
                try:
                    snapshot = json.loads(str(row[3]))
                except:
                    pass

            cue = {
                'id': str(row[0]),
                'index': int(row[1]) if row[1] else i,
                'name': str(row[2]),
                'snapshot': snapshot,
                'duration': float(row[4]) if row[4] else 0,
                'autofollow': str(row[5]).lower() == 'true' if row[5] else False,
                'actions': json.loads(str(row[6])) if row[6] else [],
                'created': str(row[7]) if len(row) > 7 else '',
                'modified': str(row[8]) if len(row) > 8 else ''
            }
            cue['component_count'] = len(snapshot)
            enabled_count = sum(1 for v in snapshot.values() if v.get('enabled', True))
            cue['enabled_count'] = enabled_count
            cues.append(cue)

        cues.sort(key=lambda c: c['index'])

        return {
            'success': True,
            'cues': cues,
            'count': len(cues),
            'current_index': _cue_state['current_index']
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def save_cue(cue_data):
    """Save or update a cue with multi-component snapshot."""
    try:
        table = get_cue_table()
        if table is None:
            return {'success': False, 'error': 'Cue table not available'}

        cue_id = cue_data.get('id')
        name = cue_data.get('name', 'Untitled')
        snapshot = cue_data.get('snapshot', {})
        duration = cue_data.get('duration', 0)
        autofollow = cue_data.get('autofollow', False)
        actions = cue_data.get('actions', [])

        import datetime
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        existing_row = None
        if cue_id:
            for i in range(1, table.numRows):
                if str(table[i, 0]) == cue_id:
                    existing_row = i
                    break

        if existing_row:
            table[existing_row, 2] = name
            table[existing_row, 3] = json.dumps(snapshot)
            table[existing_row, 4] = str(duration)
            table[existing_row, 5] = str(autofollow)
            table[existing_row, 6] = json.dumps(actions)
            table[existing_row, 8] = now
            return {
                'success': True,
                'id': cue_id,
                'updated': True,
                'component_count': len(snapshot)
            }
        else:
            import uuid
            new_id = cue_id or f'cue_{uuid.uuid4().hex[:8]}'
            max_index = 0
            for i in range(1, table.numRows):
                try:
                    idx = int(table[i, 1])
                    if idx > max_index:
                        max_index = idx
                except:
                    pass
            new_index = max_index + 1

            table.appendRow([
                new_id,
                str(new_index),
                name,
                json.dumps(snapshot),
                str(duration),
                str(autofollow),
                json.dumps(actions),
                now,
                now
            ])
            return {
                'success': True,
                'id': new_id,
                'index': new_index,
                'created': True,
                'component_count': len(snapshot)
            }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def delete_cue(cue_id):
    """Delete a cue."""
    try:
        table = get_cue_table()
        if table is None:
            return {'success': False, 'error': 'Cue table not available'}

        for i in range(1, table.numRows):
            if str(table[i, 0]) == cue_id:
                table.deleteRow(i)
                return {'success': True, 'id': cue_id, 'deleted': True}

        return {'success': False, 'error': f'Cue not found: {cue_id}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def reorder_cue(cue_id, new_index):
    """Move a cue to a new position."""
    try:
        table = get_cue_table()
        if table is None:
            return {'success': False, 'error': 'Cue table not available'}

        target_row = None
        old_index = None
        for i in range(1, table.numRows):
            if str(table[i, 0]) == cue_id:
                target_row = i
                old_index = int(table[i, 1])
                break

        if target_row is None:
            return {'success': False, 'error': f'Cue not found: {cue_id}'}

        for i in range(1, table.numRows):
            if i == target_row:
                continue
            idx = int(table[i, 1])
            if old_index < new_index:
                if old_index < idx <= new_index:
                    table[i, 1] = str(idx - 1)
            else:
                if new_index <= idx < old_index:
                    table[i, 1] = str(idx + 1)

        table[target_row, 1] = str(new_index)

        return {'success': True, 'id': cue_id, 'old_index': old_index, 'new_index': new_index}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def execute_cue(cue_id=None, index=None):
    """Execute a cue by ID or index."""
    global _cue_state
    try:
        table = get_cue_table()
        if table is None:
            return {'success': False, 'error': 'Cue table not available'}

        cue_row = None
        for i in range(1, table.numRows):
            if cue_id and str(table[i, 0]) == cue_id:
                cue_row = i
                break
            if index is not None and int(table[i, 1]) == index:
                cue_row = i
                break

        if cue_row is None:
            return {'success': False, 'error': 'Cue not found'}

        snapshot = {}
        if table[cue_row, 3]:
            try:
                snapshot = json.loads(str(table[cue_row, 3]))
            except:
                pass

        cue = {
            'id': str(table[cue_row, 0]),
            'index': int(table[cue_row, 1]),
            'name': str(table[cue_row, 2]),
            'snapshot': snapshot,
            'duration': float(table[cue_row, 4]) if table[cue_row, 4] else 0,
            'autofollow': str(table[cue_row, 5]).lower() == 'true',
            'actions': json.loads(str(table[cue_row, 6])) if table[cue_row, 6] else []
        }

        _cue_state['current_index'] = cue['index']

        results = {
            'snapshot_applied': [],
            'snapshot_errors': [],
            'actions_executed': []
        }

        for comp_path, comp_data in snapshot.items():
            if not comp_data.get('enabled', True):
                continue

            comp = op(comp_path)
            if comp is None:
                results['snapshot_errors'].append({'path': comp_path, 'error': 'Component not found'})
                continue

            params = comp_data.get('params', {})
            applied = []
            errors = []

            for param_name, value in params.items():
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
                    errors.append({'param': param_name, 'error': str(pe)})

            results['snapshot_applied'].append({
                'path': comp_path,
                'applied': len(applied),
                'errors': errors if errors else None
            })

        for action in cue['actions']:
            action_result = execute_cue_action(action)
            results['actions_executed'].append({
                'action': action,
                'result': action_result
            })

        if cue['autofollow'] and cue['duration'] > 0:
            if _cue_state['autofollow_timer']:
                try:
                    run('args[0].cancel()', _cue_state['autofollow_timer'], delayFrames=1)
                except:
                    pass

            next_index = cue['index'] + 1
            delay_frames = int(cue['duration'] * me.time.rate)
            _cue_state['autofollow_timer'] = run('execute_cue(index=args[0])', next_index, delayFrames=delay_frames)

        return {
            'success': True,
            'cue': cue,
            'results': results
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

def execute_cue_action(action):
    """Execute a single cue action."""
    try:
        action_type = action.get('type', '')

        if action_type == 'python':
            code = action.get('code', '')
            if code:
                exec(code)
            return {'success': True, 'type': 'python'}

        elif action_type == 'osc':
            address = action.get('address', '')
            args = action.get('args', [])
            port = action.get('port', 7000)
            host = action.get('host', '127.0.0.1')

            osc_out = op('/project1/mcp_bridge/oscout_cues')
            if osc_out is None:
                bridge = op('/project1/mcp_bridge')
                osc_out = bridge.create(oscoutDAT, 'oscout_cues')
                osc_out.par.address = host
                osc_out.par.port = port

            osc_out.sendOSC(address, args)
            return {'success': True, 'type': 'osc', 'address': address}

        elif action_type == 'parameter':
            op_path = action.get('path', '')
            param = action.get('parameter', '')
            value = action.get('value')
            if op_path and param:
                target = op(op_path)
                if target:
                    setattr(target.par, param, value)
                    return {'success': True, 'type': 'parameter', 'path': op_path}
            return {'success': False, 'type': 'parameter', 'error': 'Invalid path or parameter'}

        elif action_type == 'timeline':
            timeline_action = action.get('action', '')
            result_info = {'type': 'timeline', 'action': timeline_action}

            if timeline_action == 'play':
                project.play = True
                result_info['state'] = 'playing'
            elif timeline_action == 'pause':
                project.play = False
                result_info['state'] = 'paused'
            elif timeline_action == 'stop':
                project.play = False
                project.frame = 1
                result_info['state'] = 'stopped'
            elif timeline_action == 'jump_frame':
                frame = action.get('frame', 1)
                project.frame = int(frame)
                result_info['frame'] = project.frame
            elif timeline_action == 'set_rate':
                rate = action.get('rate', 1.0)
                project.rate = float(rate)
                result_info['rate'] = project.rate
            elif timeline_action == 'toggle_loop':
                project.loop = not project.loop
                result_info['loop_enabled'] = project.loop
            else:
                return {'success': False, 'type': 'timeline', 'error': f'Unknown timeline action: {timeline_action}'}

            return {'success': True, **result_info}

        else:
            return {'success': False, 'error': f'Unknown action type: {action_type}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}

def go_next():
    """Go to the next cue."""
    global _cue_state
    next_index = _cue_state['current_index'] + 1
    result = execute_cue(index=next_index)
    if not result.get('success'):
        return {'success': False, 'error': 'No more cues', 'current_index': _cue_state['current_index']}
    return result

def go_back():
    """Go to the previous cue."""
    global _cue_state
    prev_index = _cue_state['current_index'] - 1
    if prev_index < 1:
        return {'success': False, 'error': 'Already at first cue', 'current_index': _cue_state['current_index']}
    return execute_cue(index=prev_index)

def get_current_cue():
    """Get the current cue state."""
    global _cue_state
    return {
        'success': True,
        'current_index': _cue_state['current_index']
    }

# === WebSocket Functions ===

def onWebSocketOpen(webServerDAT, client, uri):
    """Called when a WebSocket client connects."""
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

def onWebSocketClose(webServerDAT, client):
    """Called when a WebSocket client disconnects."""
    global _WS_CLIENTS
    client_id = str(id(client))
    if client_id in _WS_CLIENTS:
        del _WS_CLIENTS[client_id]

def onWebSocketReceiveText(webServerDAT, client, data):
    """Called when receiving text from a WebSocket client."""
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
            broadcast_change(webServerDAT, path, param, value, exclude_client=client_id)

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

def broadcast_change(webServerDAT, path, param, value, exclude_client=None):
    """Broadcast a parameter change to all subscribed clients."""
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

# === Main Request Handler ===

def handle_request(webServerDAT, request, response):
    """Handle UI-related HTTP requests. Called by core handler."""
    uri = request['uri']
    method = request.get('method', 'GET')

    # Serve static files for /ui routes
    if uri.startswith('/ui') and method == 'GET':
        if serve_static_file(uri, response):
            response['statusCode'] = 200
            response['statusReason'] = 'OK'
            return response, True

    body = parse_body(request)
    result = None
    handled = False

    # UI endpoints
    if uri == '/ui/schema':
        result = scan_custom_parameters(body.get('path', ''))
        handled = True
    elif uri == '/ui/discover':
        result = discover_ui_components(
            body.get('path', '/project1'),
            body.get('max_depth', 3)
        )
        handled = True
    elif uri == '/ui/set':
        changes = body.get('changes', [])
        results = []
        for change in changes:
            r = set_parameter(change.get('path', ''), change.get('parameter', ''), change.get('value', ''))
            results.append(r)
        result = {'success': True, 'results': results}
        handled = True
    elif uri == '/ui/info':
        result = {
            'projectName': project.name if project else 'Untitled',
            'projectPath': project.folder if project else '',
            'tdVersion': app.version if hasattr(app, 'version') else 'unknown',
            'tdBuild': app.build if hasattr(app, 'build') else 'unknown'
        }
        handled = True
    elif uri == '/ui/components/tree':
        result = discover_ui_components_hierarchical(
            body.get('path', '/project1'),
            body.get('max_depth', 5)
        )
        handled = True

    # Preset endpoints
    elif uri == '/presets/list':
        result = list_presets(body.get('comp_path'))
        handled = True
    elif uri == '/presets/save':
        result = save_preset(body.get('name', ''), body.get('comp_path', ''))
        handled = True
    elif uri == '/presets/load':
        result = load_preset(body.get('name', ''), body.get('comp_path', ''))
        handled = True
    elif uri == '/presets/delete':
        result = delete_preset(body.get('name', ''), body.get('comp_path', ''))
        handled = True

    # Cue endpoints
    elif uri == '/cues/list':
        result = list_cues()
        handled = True
    elif uri == '/cues/save':
        result = save_cue(body)
        handled = True
    elif uri == '/cues/delete':
        result = delete_cue(body.get('id', ''))
        handled = True
    elif uri == '/cues/reorder':
        result = reorder_cue(body.get('id', ''), body.get('new_index', 1))
        handled = True
    elif uri == '/cues/go':
        cue_id = body.get('id')
        cue_index = body.get('index')
        if cue_id:
            result = execute_cue(cue_id=cue_id)
        elif cue_index is not None:
            result = execute_cue(index=int(cue_index))
        else:
            result = {'success': False, 'error': 'No cue ID or index provided'}
        handled = True
    elif uri == '/cues/next':
        result = go_next()
        handled = True
    elif uri == '/cues/back':
        result = go_back()
        handled = True
    elif uri == '/cues/current':
        result = get_current_cue()
        handled = True
    elif uri == '/cues/snapshot':
        parent_path = body.get('parent_path', '/project1')
        max_depth = body.get('max_depth', 3)
        result = snapshot_all_components(parent_path, max_depth)
        handled = True

    # Preview endpoints
    elif uri == '/preview/top' or uri.startswith('/preview/top?'):
        path = ''
        if 'pars' in request and request['pars']:
            pars = request['pars']
            if 'path' in pars:
                path = pars['path']

        if not path and '?' in uri:
            try:
                from urllib.parse import unquote
                query_str = uri.split('?', 1)[1]
                for pair in query_str.split('&'):
                    if pair.startswith('path='):
                        path = unquote(pair[5:])
                        break
            except:
                pass

        if not path:
            path = body.get('path', '')

        if not path:
            result = {'error': f'No path provided. URI was: {uri}'}
        else:
            preview_result = get_top_preview(path)
            if isinstance(preview_result, (bytes, bytearray)):
                data = bytes(preview_result)
                content_type = 'application/octet-stream'

                if len(data) >= 4:
                    if data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF:
                        content_type = 'image/jpeg'
                    elif data[0] == 0x89 and data[1] == 0x50 and data[2] == 0x4E and data[3] == 0x47:
                        content_type = 'image/png'
                    elif data[0] == 0x49 and data[1] == 0x49:
                        content_type = 'image/tiff'

                response['statusCode'] = 200
                response['statusReason'] = 'OK'
                response['Content-Type'] = content_type
                response['data'] = data
                return response, True
            else:
                result = preview_result
        handled = True
    elif uri == '/preview/chop':
        result = get_chop_preview(body.get('path', ''), body.get('max_samples', 100))
        handled = True
    elif uri == '/preview/discover':
        result = discover_previews(body.get('path', '/project1'), body.get('max_depth', 3))
        handled = True

    if handled and result is not None:
        response['statusCode'] = 200
        response['statusReason'] = 'OK'
        response['Content-Type'] = 'application/json'
        response['data'] = json.dumps(result, indent=2)
        return response, True

    return response, handled
