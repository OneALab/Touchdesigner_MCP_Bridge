# MIDI Module Handler — STUB
# MIDI note/CC input and output
# TODO: Implement full MIDI functionality


def setup(bridge_op):
    """Create MIDI-related operators in TD."""
    pass


def on_request(uri, method, body, request, response):
    """Handle MIDI HTTP requests."""
    if uri == '/midi/status':
        return {
            'success': True,
            'module': 'midi',
            'status': 'stub',
            'message': 'MIDI module is a stub — not yet implemented'
        }
    else:
        return {'error': f'Unknown MIDI endpoint: {uri}'}
