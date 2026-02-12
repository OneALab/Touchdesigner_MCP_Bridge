# DMX Module Handler — STUB
# Art-Net / sACN universe output
# TODO: Implement full DMX functionality


def setup(bridge_op):
    """Create DMX-related operators in TD."""
    pass


def on_request(uri, method, body, request, response):
    """Handle DMX HTTP requests."""
    if uri == '/dmx/status':
        return {
            'success': True,
            'module': 'dmx',
            'status': 'stub',
            'message': 'DMX module is a stub — not yet implemented'
        }
    else:
        return {'error': f'Unknown DMX endpoint: {uri}'}
