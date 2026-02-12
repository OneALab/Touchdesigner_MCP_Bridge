# Media Module Handler — STUB
# Media clip management: file browser, playlist, clip triggering
# TODO: Implement full media functionality


def setup(bridge_op):
    """Create media-related operators in TD."""
    pass


def on_request(uri, method, body, request, response):
    """Handle media HTTP requests."""
    if uri == '/media/status':
        return {
            'success': True,
            'module': 'media',
            'status': 'stub',
            'message': 'Media module is a stub — not yet implemented'
        }
    else:
        return {'error': f'Unknown media endpoint: {uri}'}
