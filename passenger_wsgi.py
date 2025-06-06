"""
WSGI entry point for cPanel Python application
"""
import sys
import os
import json

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def application(environ, start_response):
    """
    WSGI application for QRM Chatbot API
    """
    try:
        # Only import when needed to avoid startup issues
        from src.config import config
        from src.database import db_manager
        
        # Simple health check
        if environ.get('PATH_INFO', '') == '/':
            status = '200 OK'
            
            # Test database connection
            try:
                with db_manager.get_session() as session:
                    session.execute("SELECT 1")
                db_status = "connected"
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            response_data = {
                "status": "healthy",
                "message": "QRM Chatbot API is running",
                "database": db_status,
                "timestamp": str(__import__('datetime').datetime.utcnow())
            }
            
            output = json.dumps(response_data).encode('utf-8')
            response_headers = [
                ('Content-type', 'application/json'),
                ('Content-Length', str(len(output)))
            ]
            
            start_response(status, response_headers)
            return [output]
        
        # For other endpoints, return API info
        else:
            status = '200 OK'
            response_data = {
                "message": "QRM Chatbot API",
                "note": "This API provides chatbot services for WooCommerce sites",
                "endpoints": ["/", "/chat", "/search/products", "/sites"]
            }
            
            output = json.dumps(response_data).encode('utf-8')
            response_headers = [
                ('Content-type', 'application/json'),
                ('Content-Length', str(len(output)))
            ]
            
            start_response(status, response_headers)
            return [output]
            
    except Exception as e:
        # Fallback error response
        status = '500 Internal Server Error'
        error_data = {
            "error": "Internal server error",
            "message": str(e)
        }
        
        output = json.dumps(error_data).encode('utf-8')
        response_headers = [
            ('Content-type', 'application/json'),
            ('Content-Length', str(len(output)))
        ]
        
        start_response(status, response_headers)
        return [output]

# For cPanel compatibility
wsgi = application