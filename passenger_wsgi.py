"""
WSGI entry point for cPanel Python application
"""
import sys
import os

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def application(environ, start_response):
    """Minimal WSGI app for testing"""
    status = '200 OK'
    output = b'{"status": "healthy", "message": "QRM Chatbot API is running"}'
    
    response_headers = [
        ('Content-type', 'application/json'),
        ('Content-Length', str(len(output)))
    ]
    
    start_response(status, response_headers)
    return [output]

# Alternative entry points for cPanel compatibility
app = application
wsgi = application