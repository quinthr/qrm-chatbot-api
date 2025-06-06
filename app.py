"""
WSGI entry point for cPanel Python application
"""
import sys
import os
import json
import urllib.parse
from datetime import datetime

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def get_request_body(environ):
    """Get request body from WSGI environ"""
    try:
        content_length = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError, TypeError):
        content_length = 0
    
    if content_length > 0:
        body = environ['wsgi.input'].read(content_length)
        return json.loads(body.decode('utf-8'))
    return {}

def json_response(data, status='200 OK'):
    """Helper to create JSON response"""
    output = json.dumps(data).encode('utf-8')
    response_headers = [
        ('Content-type', 'application/json'),
        ('Content-Length', str(len(output))),
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type')
    ]
    return status, response_headers, [output]

def application(environ, start_response):
    """WSGI application for QRM Chatbot API"""
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')
    
    try:
        # Handle CORS preflight
        if method == 'OPTIONS':
            status, headers, response = json_response({"status": "ok"})
            start_response(status, headers)
            return response
        
        # Health check endpoint
        if path == '/' and method == 'GET':
            # Test database connection
            try:
                from src.database import db_manager
                with db_manager.get_session() as session:
                    session.execute("SELECT 1")
                db_status = "connected"
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            # Check OpenAI configuration
            try:
                from src.config import config
                openai_configured = bool(config.openai.api_key and config.openai.api_key != "")
            except:
                openai_configured = False
            
            response_data = {
                "status": "healthy",
                "message": "QRM Chatbot API is running",
                "database": db_status,
                "openai_configured": openai_configured,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            status, headers, response = json_response(response_data)
            start_response(status, headers)
            return response
        
        # Chat endpoint
        elif path == '/chat' and method == 'POST':
            data = get_request_body(environ)
            
            if not data or 'message' not in data or 'site_name' not in data:
                status, headers, response = json_response(
                    {"error": "Missing required fields: message, site_name"}, 
                    '400 Bad Request'
                )
                start_response(status, headers)
                return response
            
            # Import and use chat service
            from src.services import chat_service
            from src.database import db_manager
            from src.db_models import Site
            
            # Validate site
            with db_manager.get_session() as session:
                site = session.query(Site).filter_by(name=data['site_name']).first()
                if not site:
                    status, headers, response = json_response(
                        {"error": f"Site '{data['site_name']}' not found"}, 
                        '404 Not Found'
                    )
                    start_response(status, headers)
                    return response
            
            # Generate response
            result = chat_service.generate_response(
                message=data['message'],
                site_name=data['site_name'],
                conversation_id=data.get('conversation_id')
            )
            
            status, headers, response = json_response(result)
            start_response(status, headers)
            return response
        
        # Product search endpoint
        elif path == '/search/products' and method == 'POST':
            data = get_request_body(environ)
            
            if not data or 'site_name' not in data or 'query' not in data:
                status, headers, response = json_response(
                    {"error": "Missing required fields: site_name, query"}, 
                    '400 Bad Request'
                )
                start_response(status, headers)
                return response
            
            from src.services import knowledge_base_service
            
            products = knowledge_base_service.search_products(
                site_name=data['site_name'],
                query=data['query'],
                limit=data.get('limit', 10)
            )
            
            result = {
                "products": products,
                "total_found": len(products)
            }
            
            status, headers, response = json_response(result)
            start_response(status, headers)
            return response
        
        # Sites list endpoint
        elif path == '/sites' and method == 'GET':
            from src.database import db_manager
            from src.db_models import Site
            
            with db_manager.get_session() as session:
                sites = session.query(Site).all()
                result = [
                    {
                        "name": site.name,
                        "url": site.url,
                        "is_active": site.is_active,
                        "created_at": site.created_at.isoformat() if site.created_at else None
                    }
                    for site in sites
                ]
            
            status, headers, response = json_response(result)
            start_response(status, headers)
            return response
        
        # Default 404
        else:
            status, headers, response = json_response(
                {
                    "error": "Not Found",
                    "message": f"Endpoint {method} {path} not found",
                    "available_endpoints": [
                        "GET /",
                        "POST /chat", 
                        "POST /search/products",
                        "GET /sites"
                    ]
                }, 
                '404 Not Found'
            )
            start_response(status, headers)
            return response
            
    except Exception as e:
        # Error response
        status, headers, response = json_response(
            {
                "error": "Internal server error",
                "message": str(e)
            }, 
            '500 Internal Server Error'
        )
        start_response(status, headers)
        return response

# cPanel expects this variable
app = application