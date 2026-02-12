# OSC Module Handler
# OSC in/out with Bitfocus Companion integration
import json
import traceback


def setup(bridge_op):
    """Create OSC receiver for Companion mode."""
    existing = bridge_op.op('osc')
    if existing:
        return  # Already set up

    osc_container = bridge_op.create(baseCOMP, 'osc')
    osc_container.nodeX = 600
    osc_container.nodeY = 0

    # Create OSC receiver
    osc_in = osc_container.create(oscinDAT, 'osc_in')
    osc_in.nodeX = 0
    osc_in.nodeY = 0
    osc_in.par.port = 7000
    osc_in.par.active = True

    # Create OSC callbacks handler
    osc_callbacks = osc_container.create(textDAT, 'osc_callbacks')
    osc_callbacks.nodeX = 200
    osc_callbacks.nodeY = 0

    osc_callbacks_code = '''# OSC Callbacks - handles incoming OSC from Bitfocus Companion
#
# SIMPLE FORMAT (for Companion - single value field):
#   /td/set/project1/constant1/const0value  [value]  -> sets parameter to value
#   /td/pulse/project1/geo1/cook                     -> pulses parameter
#   /td/toggle/project1/switch1/index                -> toggles parameter
#   /td/cue/next                                     -> next cue
#   /td/cue/back                                     -> previous cue
#   /td/cue/go/mycue                                 -> go to specific cue
#
import json

def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    """Handle incoming OSC messages from Bitfocus Companion."""

    try:
        print(f"OSC IN: {address} args={args}")

        parts = address.split('/')
        if len(parts) < 3 or parts[1] != 'td':
            print(f"  Invalid OSC address (must start with /td/): {address}")
            return

        command = parts[2]

        # === PARAMETER SET ===
        if command == 'set' and len(parts) >= 5:
            param_name = parts[-1]
            op_path = '/' + '/'.join(parts[3:-1])
            if len(args) < 1:
                print(f"  ERROR: /td/set requires a value argument")
                return
            value = args[0]
            comp = op(op_path)
            if comp and hasattr(comp.par, param_name):
                setattr(comp.par, param_name, value)
                print(f"  SET: {op_path}.{param_name} = {value}")
            else:
                print(f"  ERROR: {op_path}.{param_name} not found")

        # === PARAMETER PULSE ===
        elif command == 'pulse' and len(parts) >= 5:
            param_name = parts[-1]
            op_path = '/' + '/'.join(parts[3:-1])
            comp = op(op_path)
            if comp and hasattr(comp.par, param_name):
                getattr(comp.par, param_name).pulse()
                print(f"  PULSE: {op_path}.{param_name}")
            else:
                print(f"  ERROR: {op_path}.{param_name} not found")

        # === PARAMETER TOGGLE ===
        elif command == 'toggle' and len(parts) >= 5:
            param_name = parts[-1]
            op_path = '/' + '/'.join(parts[3:-1])
            comp = op(op_path)
            if comp and hasattr(comp.par, param_name):
                par = getattr(comp.par, param_name)
                par.val = not par.val
                print(f"  TOGGLE: {op_path}.{param_name} = {par.val}")
            else:
                print(f"  ERROR: {op_path}.{param_name} not found")

        # === CUE COMMANDS ===
        elif command == 'cue':
            bridge = op('/project1/mcp_bridge')
            loaded_modules = bridge.fetch('loaded_modules', {}) if bridge else {}
            cues_handler = loaded_modules.get('cues', {}).get('handler')

            if len(parts) >= 4:
                sub_cmd = parts[3]
                if sub_cmd == 'next' and cues_handler:
                    result = cues_handler.go_next()
                    print(f"  CUE NEXT: {result}")
                elif sub_cmd == 'back' and cues_handler:
                    result = cues_handler.go_back()
                    print(f"  CUE BACK: {result}")
                elif sub_cmd == 'go' and len(parts) >= 5 and cues_handler:
                    cue_id = parts[4]
                    result = cues_handler.execute_cue(cue_id=cue_id)
                    print(f"  CUE GO {cue_id}: {result}")
                else:
                    print(f"  Unknown cue command: {sub_cmd}")

        # === PRESET ===
        elif command == 'preset' and len(parts) >= 4:
            sub_cmd = parts[3]
            if sub_cmd == 'load' and len(parts) >= 6:
                preset_name = parts[4]
                comp_path = '/' + '/'.join(parts[5:])
                bridge = op('/project1/mcp_bridge')
                loaded_modules = bridge.fetch('loaded_modules', {}) if bridge else {}
                presets_handler = loaded_modules.get('presets', {}).get('handler')
                if presets_handler:
                    result = presets_handler.load_preset(preset_name, comp_path)
                    print(f"  PRESET LOAD {preset_name} -> {comp_path}: {result}")

        # === PYTHON ===
        elif command == 'python':
            if len(args) >= 1:
                code = str(args[0])
                try:
                    exec(code)
                    print(f"  PYTHON: executed")
                except Exception as e:
                    print(f"  PYTHON ERROR: {e}")
            else:
                print(f"  ERROR: /td/python requires code as value")

        else:
            print(f"  Unknown command: {command}")

    except Exception as e:
        print(f"OSC callback error: {e}")
        import traceback
        traceback.print_exc()
'''

    osc_callbacks.text = osc_callbacks_code
    osc_in.par.callbacks = 'osc_callbacks'
    print("    Created OSC receiver on port 7000")


def on_request(uri, method, body, request, response):
    """Handle OSC HTTP requests."""
    if uri == '/osc/status':
        try:
            osc_container = op('/project1/mcp_bridge/osc')
            if osc_container is None:
                return {'success': True, 'installed': False}

            osc_in = osc_container.op('osc_in')
            return {
                'success': True,
                'installed': True,
                'active': osc_in.par.active.eval() if osc_in else False,
                'port': osc_in.par.port.eval() if osc_in else None
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    elif uri == '/osc/send':
        try:
            address = body.get('address', '')
            osc_args = body.get('args', [])
            host = body.get('host', '127.0.0.1')
            port = body.get('port', 7000)

            osc_out = op('/project1/mcp_bridge/osc/osc_out')
            if osc_out is None:
                osc_container = op('/project1/mcp_bridge/osc')
                if osc_container:
                    osc_out = osc_container.create(oscoutDAT, 'osc_out')
                    osc_out.par.address = host
                    osc_out.par.port = port

            if osc_out:
                osc_out.sendOSC(address, osc_args)
                return {'success': True, 'address': address}
            else:
                return {'success': False, 'error': 'Could not create OSC output'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    else:
        return {'error': f'Unknown OSC endpoint: {uri}'}
