# Preview Module Handler
# TOP thumbnail and CHOP data preview generation
import json
import traceback


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
            p = operator.parent()
            if p and p.path != parent_path:
                return p.name
            return None

        def should_include(operator):
            if include_nested:
                return True
            p = operator.parent()
            while p and p.path != parent_path:
                if p.type == 'baseCOMP':
                    return False
                p = p.parent()
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


def on_request(uri, method, body, request, response):
    """Handle preview HTTP requests."""
    if uri == '/preview/top' or uri.startswith('/preview/top?'):
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
            return {'error': f'No path provided. URI was: {uri}'}

        preview_result = get_top_preview(path)
        if isinstance(preview_result, (bytes, bytearray)):
            data = bytes(preview_result)
            content_type = 'application/octet-stream'

            if len(data) >= 4:
                if data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF:
                    content_type = 'image/jpeg'
                elif data[0] == 0x89 and data[1] == 0x50 and data[2] == 0x4E and data[3] == 0x47:
                    content_type = 'image/png'

            response['statusCode'] = 200
            response['statusReason'] = 'OK'
            response['Content-Type'] = content_type
            response['data'] = data
            return None  # Signal that response was handled directly

        return preview_result

    elif uri == '/preview/chop':
        return get_chop_preview(body.get('path', ''), body.get('max_samples', 100))
    elif uri == '/preview/discover':
        return discover_previews(body.get('path', '/project1'), body.get('max_depth', 3))
    else:
        return {'error': f'Unknown preview endpoint: {uri}'}
