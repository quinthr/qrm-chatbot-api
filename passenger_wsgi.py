import sys
import os

# Add your project directory to the sys.path
sys.path.insert(0, os.path.dirname(__file__))

from main import app

# ASGI to WSGI adapter for FastAPI
try:
    from asgiref.wsgi import WsgiToAsgi
    application = WsgiToAsgi(app)
except ImportError:
    # Fallback: use basic WSGI wrapper
    def application(environ, start_response):
        # Simple test response
        status = '200 OK'
        headers = [('Content-type', 'application/json')]
        start_response(status, headers)
        return [b'{"status": "API is running but ASGI adapter not available"}']