"""
Minimal WSGI test application
"""

def application(environ, start_response):
    """Minimal WSGI app for testing"""
    status = '200 OK'
    output = b'Hello World - WSGI Test'
    
    response_headers = [
        ('Content-type', 'text/plain'),
        ('Content-Length', str(len(output)))
    ]
    
    start_response(status, response_headers)
    return [output]