# Cue Module Handler
# Cue system with snapshots, actions, autofollow, go/next/back
import json
import traceback

# Global cue state
_cue_state = {
    'current_index': 0,
    'autofollow_timer': None
}


def setup(bridge_op):
    """Create cue storage table in the bridge."""
    existing = bridge_op.op('cue_storage')
    if existing is None:
        cue_table = bridge_op.create(tableDAT, 'cue_storage')
        cue_table.nodeX = 400
        cue_table.nodeY = -100
        cue_table.clear()
        cue_table.appendRow(['id', 'index', 'name', 'snapshot', 'duration', 'autofollow', 'actions', 'created', 'modified'])
        print("    Created cue_storage table")


def _get_table():
    bridge = op('/project1/mcp_bridge')
    if bridge is None:
        return None
    return bridge.op('cue_storage')


def snapshot_all_components(parent_path='/project1', max_depth=3):
    try:
        parent_op = op(parent_path)
        if parent_op is None:
            return {'success': False, 'error': f'Parent not found: {parent_path}'}

        snapshot = {}
        comps = parent_op.findChildren(type=COMP, maxDepth=max_depth)

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
    global _cue_state
    try:
        table = _get_table()
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
    try:
        table = _get_table()
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
    try:
        table = _get_table()
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
    try:
        table = _get_table()
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
    global _cue_state
    try:
        table = _get_table()
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
    global _cue_state
    next_index = _cue_state['current_index'] + 1
    result = execute_cue(index=next_index)
    if not result.get('success'):
        return {'success': False, 'error': 'No more cues', 'current_index': _cue_state['current_index']}
    return result


def go_back():
    global _cue_state
    prev_index = _cue_state['current_index'] - 1
    if prev_index < 1:
        return {'success': False, 'error': 'Already at first cue', 'current_index': _cue_state['current_index']}
    return execute_cue(index=prev_index)


def get_current_cue():
    global _cue_state
    return {
        'success': True,
        'current_index': _cue_state['current_index']
    }


def on_request(uri, method, body, request, response):
    """Handle cue HTTP requests."""
    if uri == '/cues/list':
        return list_cues()
    elif uri == '/cues/save':
        return save_cue(body)
    elif uri == '/cues/delete':
        return delete_cue(body.get('id', ''))
    elif uri == '/cues/reorder':
        return reorder_cue(body.get('id', ''), body.get('new_index', 1))
    elif uri == '/cues/go':
        cue_id = body.get('id')
        cue_index = body.get('index')
        if cue_id:
            return execute_cue(cue_id=cue_id)
        elif cue_index is not None:
            return execute_cue(index=int(cue_index))
        else:
            return {'success': False, 'error': 'No cue ID or index provided'}
    elif uri == '/cues/next':
        return go_next()
    elif uri == '/cues/back':
        return go_back()
    elif uri == '/cues/current':
        return get_current_cue()
    elif uri == '/cues/snapshot':
        parent_path = body.get('parent_path', '/project1')
        max_depth = body.get('max_depth', 3)
        return snapshot_all_components(parent_path, max_depth)
    else:
        return {'error': f'Unknown cue endpoint: {uri}'}
