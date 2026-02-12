# StreamDeck Module Handler
# TD-side config, pages, profiles, device management, and service control
import json
import os
import subprocess
import traceback


def setup(bridge_op):
    """Create StreamDeck config tables in the bridge."""
    existing = bridge_op.op('streamdeck')
    if existing:
        return  # Already set up

    sd = bridge_op.create(baseCOMP, 'streamdeck')
    sd.nodeX = 400
    sd.nodeY = 0

    # Config table
    config = sd.create(tableDAT, 'config')
    config.nodeX = 0
    config.nodeY = 0
    config.clear()
    config.appendRow(['device_serial', 'button_id', 'button_type', 'action_type', 'action_data', 'label', 'icon_path'])

    # Profiles table
    profiles = sd.create(tableDAT, 'profiles')
    profiles.nodeX = 200
    profiles.nodeY = 0
    profiles.clear()
    profiles.appendRow(['name', 'device_model', 'config_json', 'created', 'modified'])

    # Connected devices table
    devices = sd.create(tableDAT, 'connected_devices')
    devices.nodeX = 400
    devices.nodeY = 0
    devices.clear()
    devices.appendRow(['serial', 'model', 'key_count', 'has_dials', 'has_touchscreen', 'last_seen'])

    # Pages table
    pages = sd.create(tableDAT, 'pages')
    pages.nodeX = 600
    pages.nodeY = 0
    pages.clear()
    pages.appendRow(['name', 'device_type', 'device_serial', 'buttons_json', 'created', 'modified'])

    # Active pages table
    active_pages = sd.create(tableDAT, 'active_pages')
    active_pages.nodeX = 800
    active_pages.nodeY = 0
    active_pages.clear()
    active_pages.appendRow(['device_serial', 'page_name', 'activated_at'])

    # Service manager
    service_mgr = sd.create(baseCOMP, 'service_manager')
    service_mgr.nodeX = 0
    service_mgr.nodeY = -200

    ext_dat = service_mgr.create(textDAT, 'ServiceManagerExt')
    ext_dat.nodeX = 0
    ext_dat.nodeY = 0

    service_mgr_code = _get_service_manager_code()
    ext_dat.text = service_mgr_code

    service_mgr.par.extension1 = 'ServiceManagerExt'
    service_mgr.par.promoteextension1 = True

    try:
        ServiceManagerClass = ext_dat.module.ServiceManager
        instance = ServiceManagerClass(service_mgr)
        service_mgr.store('ServiceManager', instance)
        print("    ServiceManager extension instantiated")
    except Exception as e:
        print(f"    WARNING: Could not instantiate ServiceManager: {e}")

    print("    Created StreamDeck module with config tables")


# === Table accessors ===

def _sd():
    return op('/project1/mcp_bridge/streamdeck')

def _config_table():
    sd = _sd()
    return sd.op('config') if sd else None

def _profiles_table():
    sd = _sd()
    return sd.op('profiles') if sd else None

def _devices_table():
    sd = _sd()
    if sd is None:
        return None
    t = sd.op('connected_devices')
    if t is None:
        t = sd.create(tableDAT, 'connected_devices')
        t.clear()
        t.appendRow(['serial', 'model', 'key_count', 'has_dials', 'has_touchscreen', 'last_seen'])
    return t

def _pages_table():
    sd = _sd()
    return sd.op('pages') if sd else None

def _active_pages_table():
    sd = _sd()
    return sd.op('active_pages') if sd else None


# === Config CRUD ===

def get_config(device_serial=None):
    try:
        table = _config_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        config = {}
        for i in range(1, table.numRows):
            row = table.row(i)
            serial = str(row[0])
            btn_id = str(row[1])
            btn_type = str(row[2])

            if device_serial and serial != device_serial:
                continue

            key = f"{serial}:{btn_type}:{btn_id}"
            action_data = str(row[4])
            try:
                action = json.loads(action_data) if action_data else {}
            except:
                action = {'raw': action_data}

            config[key] = {
                'device_serial': serial,
                'button_id': btn_id,
                'button_type': btn_type,
                'action_type': str(row[3]),
                'action': action,
                'label': str(row[5]),
                'icon_path': str(row[6]) if len(row) > 6 else ''
            }

        return {'success': True, 'config': config, 'count': len(config)}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def set_config(device_serial, button_id, button_type, action_type, action_data, label='', icon_path=''):
    try:
        table = _config_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        action_str = json.dumps(action_data) if isinstance(action_data, dict) else str(action_data)

        existing_row = None
        for i in range(1, table.numRows):
            if (str(table[i, 0]) == device_serial and
                str(table[i, 1]) == str(button_id) and
                str(table[i, 2]) == button_type):
                existing_row = i
                break

        if existing_row:
            table[existing_row, 3] = action_type
            table[existing_row, 4] = action_str
            table[existing_row, 5] = label
            if len(table.row(existing_row)) > 6:
                table[existing_row, 6] = icon_path
        else:
            table.appendRow([device_serial, str(button_id), button_type, action_type, action_str, label, icon_path])

        return {'success': True, 'device_serial': device_serial, 'button_id': button_id}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def delete_config(device_serial, button_id, button_type):
    try:
        table = _config_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        deleted = False
        for i in range(table.numRows - 1, 0, -1):
            if (str(table[i, 0]) == str(device_serial) and
                str(table[i, 1]) == str(button_id) and
                str(table[i, 2]) == str(button_type)):
                table.deleteRow(i)
                deleted = True

        return {'success': True, 'deleted': deleted}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# === Profiles ===

def list_profiles():
    try:
        table = _profiles_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        profiles = []
        for i in range(1, table.numRows):
            row = table.row(i)
            name = str(row[0])
            config_json = str(row[2]) if len(row) > 2 else ''
            if name == 'name' or not config_json.startswith('{'):
                continue
            profiles.append({
                'name': name,
                'device_model': str(row[1]),
                'created': str(row[3]) if len(row) > 3 else '',
                'modified': str(row[4]) if len(row) > 4 else ''
            })
        return {'success': True, 'profiles': profiles, 'count': len(profiles)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def save_profile(name, device_model=None):
    try:
        table = _profiles_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        config_result = get_config()
        if not config_result.get('success'):
            return config_result

        config_json = json.dumps(config_result.get('config', {}))
        import datetime
        now = datetime.datetime.now().isoformat()

        existing_row = None
        for i in range(1, table.numRows):
            if str(table[i, 0]) == name:
                existing_row = i
                break

        if existing_row:
            table[existing_row, 1] = device_model or ''
            table[existing_row, 2] = config_json
            table[existing_row, 4] = now
        else:
            table.appendRow([name, device_model or '', config_json, now, now])

        return {'success': True, 'name': name, 'saved': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def load_profile(name):
    try:
        config_table = _config_table()
        profiles_table = _profiles_table()
        if config_table is None or profiles_table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        profile_row = None
        for i in range(1, profiles_table.numRows):
            if str(profiles_table[i, 0]) == name:
                profile_row = i
                break

        if profile_row is None:
            return {'success': False, 'error': f'Profile not found: {name}'}

        config = json.loads(str(profiles_table[profile_row, 2]))

        while config_table.numRows > 1:
            config_table.deleteRow(1)

        for key, item in config.items():
            config_table.appendRow([
                item.get('device_serial', ''),
                item.get('button_id', ''),
                item.get('button_type', 'key'),
                item.get('action_type', ''),
                json.dumps(item.get('action', {})),
                item.get('label', ''),
                item.get('icon_path', '')
            ])

        return {'success': True, 'name': name, 'loaded': True, 'button_count': len(config)}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def delete_profile(name):
    try:
        table = _profiles_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}
        for i in range(1, table.numRows):
            if str(table[i, 0]) == name:
                table.deleteRow(i)
                return {'success': True, 'name': name, 'deleted': True}
        return {'success': False, 'error': f'Profile not found: {name}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# === Devices ===

def report_devices(devices):
    try:
        table = _devices_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        import datetime
        now = datetime.datetime.now().isoformat()

        while table.numRows > 1:
            table.deleteRow(1)

        for dev in devices:
            table.appendRow([
                dev.get('serial', ''),
                dev.get('model', ''),
                str(dev.get('key_count', 0)),
                str(dev.get('has_dials', False)),
                str(dev.get('has_touchscreen', False)),
                now
            ])

        return {'success': True, 'device_count': len(devices), 'timestamp': now}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def list_devices():
    try:
        table = _devices_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        devices = []
        for i in range(1, table.numRows):
            row = table.row(i)
            devices.append({
                'serial': str(row[0]),
                'model': str(row[1]),
                'key_count': int(row[2]) if row[2] else 0,
                'has_dials': str(row[3]).lower() == 'true',
                'has_touchscreen': str(row[4]).lower() == 'true',
                'last_seen': str(row[5]) if len(row) > 5 else ''
            })
        return {'success': True, 'devices': devices, 'count': len(devices)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# === Pages ===

def pages_list():
    try:
        table = _pages_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        pages = []
        for i in range(1, table.numRows):
            row = table.row(i)
            name = str(row[0])
            if name == 'name':
                continue
            pages.append({
                'name': name,
                'device_type': str(row[1]),
                'device_serial': str(row[2]),
                'created': str(row[4]) if len(row) > 4 else '',
                'modified': str(row[5]) if len(row) > 5 else ''
            })
        return {'success': True, 'pages': pages, 'count': len(pages)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def pages_get(name):
    try:
        table = _pages_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        for i in range(1, table.numRows):
            if str(table[i, 0]) == name:
                buttons_json = str(table[i, 3])
                try:
                    buttons = json.loads(buttons_json) if buttons_json else {}
                except:
                    buttons = {}
                return {
                    'success': True,
                    'page': {
                        'name': name,
                        'device_type': str(table[i, 1]),
                        'device_serial': str(table[i, 2]),
                        'buttons': buttons,
                        'created': str(table[i, 4]) if table.numCols > 4 else '',
                        'modified': str(table[i, 5]) if table.numCols > 5 else ''
                    }
                }
        return {'success': False, 'error': f'Page not found: {name}'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def pages_save(name, device_type, device_serial, buttons):
    try:
        table = _pages_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        import datetime
        now = datetime.datetime.now().isoformat()
        buttons_json = json.dumps(buttons)

        existing_row = None
        for i in range(1, table.numRows):
            if str(table[i, 0]) == name:
                existing_row = i
                break

        if existing_row:
            table[existing_row, 1] = device_type
            table[existing_row, 2] = device_serial or ''
            table[existing_row, 3] = buttons_json
            table[existing_row, 5] = now
            return {'success': True, 'name': name, 'updated': True}
        else:
            table.appendRow([name, device_type, device_serial or '', buttons_json, now, now])
            return {'success': True, 'name': name, 'created': True}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def pages_delete(name):
    try:
        table = _pages_table()
        if table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}
        for i in range(1, table.numRows):
            if str(table[i, 0]) == name:
                table.deleteRow(i)
                return {'success': True, 'deleted': name}
        return {'success': False, 'error': f'Page not found: {name}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def pages_activate(device_serial, page_name):
    try:
        active_table = _active_pages_table()
        pages_table = _pages_table()
        if active_table is None or pages_table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        page_found = any(str(pages_table[i, 0]) == page_name for i in range(1, pages_table.numRows))
        if not page_found:
            return {'success': False, 'error': f'Page not found: {page_name}'}

        import datetime
        now = datetime.datetime.now().isoformat()

        existing_row = None
        for i in range(1, active_table.numRows):
            if str(active_table[i, 0]) == device_serial:
                existing_row = i
                break

        if existing_row:
            active_table[existing_row, 1] = page_name
            active_table[existing_row, 2] = now
        else:
            active_table.appendRow([device_serial, page_name, now])

        return {'success': True, 'device_serial': device_serial, 'page_name': page_name}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def get_active_page(device_serial, device_type=None):
    try:
        active_table = _active_pages_table()
        pages_table = _pages_table()
        if active_table is None or pages_table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        active_page_name = None
        for i in range(1, active_table.numRows):
            if str(active_table[i, 0]) == device_serial:
                active_page_name = str(active_table[i, 1])
                break

        if not active_page_name and device_type:
            for i in range(1, pages_table.numRows):
                page_serial = str(pages_table[i, 2])
                page_type = str(pages_table[i, 1])
                if page_serial == device_serial:
                    active_page_name = str(pages_table[i, 0])
                    break
                elif page_type == device_type and page_serial == '':
                    active_page_name = str(pages_table[i, 0])

        if not active_page_name:
            return {'success': True, 'page': None, 'message': 'No page assigned'}

        return pages_get(active_page_name)
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def get_all_active_pages():
    try:
        devices_table = _devices_table()
        if devices_table is None:
            return {'success': False, 'error': 'Stream Deck module not found.'}

        result = {}
        for i in range(1, devices_table.numRows):
            serial = str(devices_table[i, 0])
            model = str(devices_table[i, 1])

            model_lower = model.lower()
            if 'mini' in model_lower:
                device_type = 'mini'
            elif 'xl' in model_lower:
                device_type = 'xl'
            elif 'plus' in model_lower or '+' in model_lower:
                device_type = 'plus'
            elif 'neo' in model_lower:
                device_type = 'neo'
            elif 'pedal' in model_lower:
                device_type = 'pedal'
            else:
                device_type = 'standard'

            page_result = get_active_page(serial, device_type)
            if page_result.get('success') and page_result.get('page'):
                result[serial] = page_result['page']

        return {'success': True, 'active_pages': result}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


# === Service control ===

def _get_service_manager():
    sd = _sd()
    if sd is None:
        return None
    mgr = sd.op('service_manager')
    if mgr is None:
        return None
    if hasattr(mgr, 'ext') and hasattr(mgr.ext, 'ServiceManager'):
        return mgr.ext.ServiceManager
    ext = mgr.fetch('ServiceManager')
    if ext is not None:
        return ext
    ext_dat = mgr.op('ServiceManagerExt')
    if ext_dat and hasattr(ext_dat, 'module'):
        try:
            cls = ext_dat.module.ServiceManager
            instance = cls(mgr)
            mgr.store('ServiceManager', instance)
            return instance
        except:
            pass
    return None


def get_status():
    try:
        sd = _sd()
        if sd is None:
            return {'success': True, 'installed': False, 'message': 'Stream Deck module not installed.'}

        config_table = sd.op('config')
        profiles_table = sd.op('profiles')
        osc_container = op('/project1/mcp_bridge/osc')
        osc_in = osc_container.op('osc_in') if osc_container else None

        return {
            'success': True,
            'installed': True,
            'config_count': config_table.numRows - 1 if config_table else 0,
            'profile_count': profiles_table.numRows - 1 if profiles_table else 0,
            'osc_active': osc_in.par.active.eval() if osc_in else False,
            'osc_port': osc_in.par.port.eval() if osc_in else None
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def service_start():
    try:
        mgr = _get_service_manager()
        if mgr is None:
            return {'success': False, 'error': 'Service manager not found.'}
        result = mgr.Start()
        return {'success': result, 'running': mgr.IsRunning, 'pid': mgr.PID}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def service_stop():
    try:
        mgr = _get_service_manager()
        if mgr is None:
            return {'success': False, 'error': 'Service manager not found.'}
        mgr.Stop()
        return {'success': True, 'running': mgr.IsRunning, 'pid': mgr.PID}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def service_restart():
    try:
        mgr = _get_service_manager()
        if mgr is None:
            return {'success': False, 'error': 'Service manager not found.'}
        result = mgr.Restart()
        return {'success': result, 'running': mgr.IsRunning, 'pid': mgr.PID}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def service_status():
    try:
        mgr = _get_service_manager()
        if mgr is None:
            return {'success': True, 'installed': False, 'running': False, 'pid': None, 'autostart': False}
        status = mgr.GetStatus()
        return {'success': True, 'installed': True, **status}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def service_autostart(body):
    try:
        mgr = _get_service_manager()
        if mgr is None:
            return {'success': False, 'error': 'Service manager not found.'}
        enabled = body.get('enabled', False)
        mgr.SetAutoStart(enabled)
        return {'success': True, 'autostart': enabled}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# === Companion export ===

def export_companion(profile_name=None):
    try:
        if profile_name:
            profiles_table = _profiles_table()
            if profiles_table is None:
                return {'success': False, 'error': 'Stream Deck module not found.'}
            profile_row = None
            for i in range(1, profiles_table.numRows):
                if str(profiles_table[i, 0]) == profile_name:
                    profile_row = i
                    break
            if profile_row is None:
                return {'success': False, 'error': f'Profile not found: {profile_name}'}
            config = json.loads(str(profiles_table[profile_row, 2]))
        else:
            config_result = get_config()
            if not config_result.get('success'):
                return config_result
            config = config_result.get('config', {})

        companion_buttons = []
        for key, item in config.items():
            action_type = item.get('action_type', '')
            action = item.get('action', {})
            label = item.get('label', '')
            btn_id = item.get('button_id', '')

            osc_address = ''
            osc_args = []

            if action_type == 'preset':
                osc_address = '/td/preset/load'
                osc_args = [action.get('preset_name', ''), action.get('comp_path', '')]
            elif action_type == 'cue_next':
                osc_address = '/td/cue/next'
            elif action_type == 'cue_back':
                osc_address = '/td/cue/back'
            elif action_type == 'cue_go':
                osc_address = '/td/cue/go'
                osc_args = [action.get('cue_id', '')]
            elif action_type == 'parameter':
                osc_address = '/td/param/set'
                osc_args = [action.get('path', ''), action.get('param', ''), action.get('value', 0)]
            elif action_type == 'pulse':
                osc_address = '/td/param/pulse'
                osc_args = [action.get('path', ''), action.get('param', '')]
            elif action_type == 'toggle':
                osc_address = '/td/param/toggle'
                osc_args = [action.get('path', ''), action.get('param', '')]
            elif action_type == 'python':
                osc_address = '/td/python'
                osc_args = [action.get('code', '')]

            if osc_address:
                companion_buttons.append({
                    'button_id': btn_id,
                    'label': label,
                    'osc_address': osc_address,
                    'osc_args': osc_args
                })

        return {
            'success': True,
            'companion_config': {
                'type': 'td_streamdeck_export',
                'version': 1,
                'td_osc_port': 7000,
                'td_osc_host': '127.0.0.1',
                'buttons': companion_buttons,
            },
            'button_count': len(companion_buttons)
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


# === Service Manager Extension Code ===

def _get_service_manager_code():
    return '''# Service Manager - controls external streamdeck service process
import subprocess
import os

class ServiceManager:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.process = None
        self._pid = None
        run('ext = op("{}").fetch("ServiceManager"); ext._checkAutoStart() if ext else None'.format(ownerComp.path), delayFrames=60)

    def _checkAutoStart(self):
        sd = self.ownerComp.parent()
        if sd and sd.fetch('autostart_service', False):
            print("Auto-starting Stream Deck service...")
            self.Start()

    def SetAutoStart(self, enabled):
        sd = self.ownerComp.parent()
        if sd:
            sd.store('autostart_service', bool(enabled))
            print("Stream Deck service auto-start: {}".format('ENABLED' if enabled else 'DISABLED'))

    @property
    def IsRunning(self):
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def PID(self):
        if self.IsRunning:
            return self._pid
        return None

    def Start(self):
        if self.IsRunning:
            print("Stream Deck service already running (PID: {})".format(self._pid))
            return True

        bridge_folder = None
        for candidate in [project.folder, os.path.join(project.folder, '_mcp_bridge')]:
            script_path = os.path.join(candidate, 'modules', 'mod_streamdeck', 'service.py')
            if os.path.exists(script_path):
                bridge_folder = candidate
                break
            # Fallback to root-level streamdeck_service.py
            script_path = os.path.join(candidate, 'streamdeck_service.py')
            if os.path.exists(script_path):
                bridge_folder = candidate
                break

        if bridge_folder is None:
            print("ERROR: Could not find streamdeck service script")
            return False

        # Find service script
        service_script = os.path.join(bridge_folder, 'modules', 'mod_streamdeck', 'service.py')
        if not os.path.exists(service_script):
            service_script = os.path.join(bridge_folder, 'streamdeck_service.py')
        if not os.path.exists(service_script):
            print("ERROR: Service script not found")
            return False

        venv_python = os.path.join(bridge_folder, 'streamdeck_venv', 'Scripts', 'python.exe')
        if not os.path.exists(venv_python):
            venv_python = os.path.join(bridge_folder, 'streamdeck_venv', 'bin', 'python')
        if not os.path.exists(venv_python):
            print("ERROR: streamdeck_venv not found")
            return False

        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                [venv_python, service_script],
                cwd=bridge_folder,
                startupinfo=startupinfo,
                creationflags=creationflags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._pid = self.process.pid
            print("Stream Deck service started (PID: {})".format(self._pid))
            return True
        except Exception as e:
            print("Failed to start Stream Deck service: {}".format(e))
            return False

    def Stop(self):
        if self.process is None:
            print("Stream Deck service not running")
            return
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("Stream Deck service stopped")
        except Exception as e:
            print("Error stopping service: {}".format(e))
        finally:
            self.process = None
            self._pid = None

    def Restart(self):
        self.Stop()
        return self.Start()

    def GetStatus(self):
        sd = self.ownerComp.parent()
        autostart = sd.fetch('autostart_service', False) if sd else False
        return {
            'running': self.IsRunning,
            'pid': self.PID,
            'autostart': autostart
        }
'''


# === HTTP Router ===

def on_request(uri, method, body, request, response):
    """Handle StreamDeck HTTP requests."""
    # Status
    if uri == '/streamdeck/status':
        return get_status()

    # Config
    elif uri == '/streamdeck/config/get':
        return get_config(body.get('device_serial'))
    elif uri == '/streamdeck/config/set':
        return set_config(
            body.get('device_serial', ''), body.get('button_id', ''),
            body.get('button_type', 'key'), body.get('action_type', ''),
            body.get('action', {}), body.get('label', ''), body.get('icon_path', '')
        )
    elif uri == '/streamdeck/config/delete':
        return delete_config(body.get('device_serial', ''), body.get('button_id', ''), body.get('button_type', 'key'))

    # Profiles
    elif uri == '/streamdeck/profiles/list':
        return list_profiles()
    elif uri == '/streamdeck/profiles/save':
        return save_profile(body.get('name', ''), body.get('device_model'))
    elif uri == '/streamdeck/profiles/load':
        return load_profile(body.get('name', ''))
    elif uri == '/streamdeck/profiles/delete':
        return delete_profile(body.get('name', ''))
    elif uri == '/streamdeck/export/companion':
        return export_companion(body.get('profile_name'))

    # Devices
    elif uri == '/streamdeck/devices/report':
        return report_devices(body.get('devices', []))
    elif uri == '/streamdeck/devices/list':
        return list_devices()

    # Pages
    elif uri == '/streamdeck/pages/list':
        return pages_list()
    elif uri == '/streamdeck/pages/get':
        return pages_get(body.get('name', ''))
    elif uri == '/streamdeck/pages/save':
        return pages_save(body.get('name', ''), body.get('device_type', 'standard'),
                         body.get('device_serial', ''), body.get('buttons', {}))
    elif uri == '/streamdeck/pages/delete':
        return pages_delete(body.get('name', ''))
    elif uri == '/streamdeck/pages/activate':
        return pages_activate(body.get('device_serial', ''), body.get('page_name', ''))
    elif uri == '/streamdeck/pages/active':
        return get_active_page(body.get('device_serial', ''), body.get('device_type'))
    elif uri == '/streamdeck/pages/all-active':
        return get_all_active_pages()

    # Service control
    elif uri == '/streamdeck/service/start':
        return service_start()
    elif uri == '/streamdeck/service/stop':
        return service_stop()
    elif uri == '/streamdeck/service/restart':
        return service_restart()
    elif uri == '/streamdeck/service/status':
        return service_status()
    elif uri == '/streamdeck/service/autostart':
        return service_autostart(body)

    else:
        return {'error': f'Unknown StreamDeck endpoint: {uri}'}
