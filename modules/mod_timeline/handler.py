# Timeline Module Handler
# Play/pause/stop/jump/rate/loop control for TD timeline
import json
import traceback


def timeline_control(action, **kwargs):
    """Execute a timeline control action."""
    try:
        result_info = {'type': 'timeline', 'action': action}

        if action == 'play':
            project.play = True
            result_info['state'] = 'playing'
        elif action == 'pause':
            project.play = False
            result_info['state'] = 'paused'
        elif action == 'stop':
            project.play = False
            project.frame = 1
            result_info['state'] = 'stopped'
        elif action == 'jump_frame':
            frame = kwargs.get('frame', 1)
            project.frame = int(frame)
            result_info['frame'] = project.frame
        elif action == 'set_rate':
            rate = kwargs.get('rate', 1.0)
            project.rate = float(rate)
            result_info['rate'] = project.rate
        elif action == 'toggle_loop':
            project.loop = not project.loop
            result_info['loop_enabled'] = project.loop
        elif action == 'status':
            result_info['playing'] = project.play
            result_info['frame'] = project.frame
            result_info['rate'] = project.rate
            result_info['loop'] = project.loop
        else:
            return {'success': False, 'error': f'Unknown timeline action: {action}'}

        return {'success': True, **result_info}
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


def on_request(uri, method, body, request, response):
    """Handle timeline HTTP requests."""
    action = uri.replace('/timeline/', '').replace('/timeline', '')

    if not action or action == '/':
        action = body.get('action', 'status')

    return timeline_control(action, **body)
