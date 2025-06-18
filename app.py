"""
WSGI entry point for cPanel Python application
Complete implementation with all debugging endpoints
"""
import sys
import os
import json
import traceback
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
    output = json.dumps(data, default=str).encode('utf-8')
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
        
        # DEBUGGING ENDPOINTS (from main.py)
        
        # Simple ping endpoint
        if path == '/ping' and method == 'GET':
            response_data = {
                "status": "ok", 
                "message": "API is responding",
                "server": "WSGI app.py"
            }
            status, headers, response = json_response(response_data)
            start_response(status, headers)
            return response
        
        # Test database connection
        elif path == '/test-db' and method == 'GET':
            try:
                from src.database import db_manager
                from src.db_models import Site
                with db_manager.get_session() as session:
                    # Simple query to test connection
                    count = session.query(Site).count()
                    response_data = {"status": "ok", "site_count": count}
            except Exception as e:
                response_data = {
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
                status, headers, response = json_response(response_data, '500 Internal Server Error')
                start_response(status, headers)
                return response
            
            status, headers, response = json_response(response_data)
            start_response(status, headers)
            return response
        
        # Database schema inspection
        elif path == '/db-schema' and method == 'GET':
            try:
                from sqlalchemy import inspect, text
                from src.database import db_manager
                from src.config import config
                
                with db_manager.get_session() as session:
                    # Get the inspector
                    inspector = inspect(db_manager.engine)
                    
                    # Get all table names
                    tables = inspector.get_table_names()
                    
                    schema_info = {
                        "database_url": config.database.url.split('@')[1] if '@' in config.database.url else "hidden",
                        "tables": {}
                    }
                    
                    # For each table, get column information
                    for table_name in sorted(tables):
                        columns = []
                        try:
                            # Get columns using inspector
                            for col in inspector.get_columns(table_name):
                                col_info = {
                                    "name": col['name'],
                                    "type": str(col['type']),
                                    "nullable": col.get('nullable', True),
                                    "default": str(col.get('default', '')) if col.get('default') else None,
                                    "primary_key": col.get('primary_key', False)
                                }
                                columns.append(col_info)
                            
                            # Get primary keys
                            pk_constraint = inspector.get_pk_constraint(table_name)
                            primary_keys = pk_constraint.get('constrained_columns', [])
                            
                            # Get foreign keys
                            foreign_keys = []
                            for fk in inspector.get_foreign_keys(table_name):
                                foreign_keys.append({
                                    "columns": fk['constrained_columns'],
                                    "referred_table": fk['referred_table'],
                                    "referred_columns": fk['referred_columns']
                                })
                            
                            # Get row count
                            row_count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                            
                            schema_info["tables"][table_name] = {
                                "columns": columns,
                                "primary_keys": primary_keys,
                                "foreign_keys": foreign_keys,
                                "row_count": row_count
                            }
                            
                        except Exception as e:
                            schema_info["tables"][table_name] = {
                                "error": f"Could not inspect table: {str(e)}"
                            }
                    
                    # Also include expected tables from our models
                    from src.db_models import Base
                    expected_tables = []
                    for mapper in Base.registry.mappers:
                        expected_tables.append(mapper.class_.__tablename__)
                    
                    schema_info["expected_tables"] = sorted(list(set(expected_tables)))
                    schema_info["missing_tables"] = [t for t in expected_tables if t not in tables]
                    schema_info["extra_tables"] = [t for t in tables if t not in expected_tables]
                    
                    status, headers, response = json_response(schema_info)
                    start_response(status, headers)
                    return response
                    
            except Exception as e:
                error_data = {
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
                status, headers, response = json_response(error_data, '500 Internal Server Error')
                start_response(status, headers)
                return response
        
        # Check models endpoint
        elif path == '/check-models' and method == 'GET':
            try:
                from src import db_models
                from src.database import db_manager
                
                results = {}
                
                with db_manager.get_session() as session:
                    # List of all models to check
                    models_to_check = [
                        ("Site", db_models.Site),
                        ("Product", db_models.Product),
                        ("ProductVariation", db_models.ProductVariation),
                        ("Category", db_models.Category),
                        ("ShippingZone", db_models.ShippingZone),
                        ("ShippingMethod", db_models.ShippingMethod),
                        ("ShippingClass", db_models.ShippingClass),
                        ("ShippingClassRate", db_models.ShippingClassRate),
                        ("Conversation", db_models.Conversation),
                        ("ConversationMessage", db_models.ConversationMessage),
                        ("CrawlLog", db_models.CrawlLog)
                    ]
                    
                    for model_name, model_class in models_to_check:
                        try:
                            # Try to query the model
                            count = session.query(model_class).count()
                            
                            # Get first record if exists
                            first_record = session.query(model_class).first()
                            
                            # Get column names from the model
                            columns = [c.name for c in model_class.__table__.columns]
                            
                            results[model_name] = {
                                "status": "ok",
                                "table_name": model_class.__tablename__,
                                "row_count": count,
                                "has_data": first_record is not None,
                                "columns": columns,
                                "column_count": len(columns)
                            }
                            
                        except Exception as e:
                            results[model_name] = {
                                "status": "error",
                                "table_name": getattr(model_class, '__tablename__', 'unknown'),
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                
                # Summary
                summary = {
                    "total_models": len(models_to_check),
                    "successful": sum(1 for r in results.values() if r["status"] == "ok"),
                    "failed": sum(1 for r in results.values() if r["status"] == "error"),
                    "models_with_data": sum(1 for r in results.values() if r.get("has_data", False))
                }
                
                response_data = {
                    "summary": summary,
                    "models": results
                }
                
                status, headers, response = json_response(response_data)
                start_response(status, headers)
                return response
                
            except Exception as e:
                error_data = {
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
                status, headers, response = json_response(error_data, '500 Internal Server Error')
                start_response(status, headers)
                return response
        
        # MAIN APPLICATION ENDPOINTS
        
        # Health check endpoint
        elif path == '/' and method == 'GET':
            try:
                # Test database connection
                from src.database import db_manager
                from sqlalchemy import text
                with db_manager.get_session() as session:
                    session.execute(text("SELECT 1"))
                db_connected = True
            except Exception:
                db_connected = False
            
            # ChromaDB disabled for hosting compatibility
            vector_db_connected = False
            
            # Check OpenAI configuration
            try:
                from src.config import config
                openai_configured = bool(config.openai.api_key and config.openai.api_key != "")
            except:
                openai_configured = False
            
            status_code = "healthy" if db_connected and openai_configured else "degraded"
            
            response_data = {
                "status": status_code,
                "timestamp": datetime.utcnow(),
                "database_connected": db_connected,
                "vector_db_connected": vector_db_connected,
                "openai_configured": openai_configured,
                "server": "WSGI app.py"
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
            
            try:
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
                
                # Generate response (simplified - no threading for now)
                try:
                    result = chat_service.generate_response(
                        message=data['message'],
                        site_name=data['site_name'],
                        conversation_id=data.get('conversation_id'),
                        user_id=data.get('user_id')
                    )
                except Exception as service_error:
                    # Extract the actual error from RetryError
                    error_message = str(service_error)
                    error_type = type(service_error).__name__
                    
                    # Try to extract the underlying error from RetryError
                    if "RetryError" in str(type(service_error)):
                        # Try multiple ways to get the underlying error
                        underlying_error = None
                        
                        # Method 1: Check __cause__
                        if hasattr(service_error, '__cause__') and service_error.__cause__:
                            underlying_error = service_error.__cause__
                        # Method 2: Check last_attempt
                        elif hasattr(service_error, 'last_attempt') and hasattr(service_error.last_attempt, 'exception'):
                            underlying_error = service_error.last_attempt.exception()
                        # Method 3: Parse from string representation
                        elif "raised" in str(service_error):
                            import re
                            match = re.search(r'raised (\\w+)', str(service_error))
                            if match:
                                error_type = match.group(1)
                                error_message = f"{error_type}: Database connection error - check logs for details"
                        
                        if underlying_error:
                            error_type = type(underlying_error).__name__
                            error_message = str(underlying_error)
                    
                    error_data = {
                        "error": "Chat service internal error",
                        "error_type": error_type,
                        "error_message": error_message,
                        "traceback": traceback.format_exc()
                    }
                    
                    status, headers, response = json_response(error_data, '500 Internal Server Error')
                    start_response(status, headers)
                    return response
                
                status, headers, response = json_response(result)
                start_response(status, headers)
                return response
                
            except Exception as chat_error:
                status, headers, response = json_response(
                    {
                        "error": "Chat service error", 
                        "error_type": type(chat_error).__name__,
                        "error_message": str(chat_error),
                        "traceback": traceback.format_exc()
                    }, 
                    '500 Internal Server Error'
                )
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
            
            try:
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
            except Exception as e:
                status, headers, response = json_response(
                    {"error": "Error searching products", "message": str(e)}, 
                    '500 Internal Server Error'
                )
                start_response(status, headers)
                return response
        
        # Sites list endpoint
        elif path == '/sites' and method == 'GET':
            try:
                from src.database import db_manager
                from src.db_models import Site
                
                with db_manager.get_session() as session:
                    sites = session.query(Site).all()
                    result = [
                        {
                            "name": site.name,
                            "url": site.url,
                            "is_active": site.is_active,
                            "created_at": site.created_at
                        }
                        for site in sites
                    ]
                
                status, headers, response = json_response(result)
                start_response(status, headers)
                return response
            except Exception as e:
                status, headers, response = json_response(
                    {"error": "Error listing sites", "message": str(e)}, 
                    '500 Internal Server Error'
                )
                start_response(status, headers)
                return response
        
        # Site stats endpoint
        elif path.startswith('/sites/') and path.endswith('/stats') and method == 'GET':
            # Extract site_name from path: /sites/{site_name}/stats
            path_parts = path.strip('/').split('/')
            if len(path_parts) == 3 and path_parts[0] == 'sites' and path_parts[2] == 'stats':
                site_name = path_parts[1]
                try:
                    from src.database import db_manager
                    from src.db_models import Site, Product, Category
                    
                    with db_manager.get_session() as session:
                        site = session.query(Site).filter_by(name=site_name).first()
                        if not site:
                            status, headers, response = json_response(
                                {"error": "Site not found"}, 
                                '404 Not Found'
                            )
                            start_response(status, headers)
                            return response
                        
                        product_count = session.query(Product).filter_by(site_id=site.id).count()
                        category_count = session.query(Category).filter_by(site_id=site.id).count()
                        
                        result = {
                            "site_name": site_name,
                            "product_count": product_count,
                            "category_count": category_count,
                            "last_updated": site.updated_at
                        }
                    
                    status, headers, response = json_response(result)
                    start_response(status, headers)
                    return response
                except Exception as e:
                    status, headers, response = json_response(
                        {"error": "Error getting site stats", "message": str(e)}, 
                        '500 Internal Server Error'
                    )
                    start_response(status, headers)
                    return response
        
        # Shipping calculate endpoint
        elif path == '/shipping/calculate' and method == 'POST':
            data = get_request_body(environ)
            
            try:
                from src.services import knowledge_base_service
                from src.database import db_manager
                
                # Calculate cart total from items
                cart_total = 0.0
                if data.get('items'):
                    with db_manager.get_session() as session:
                        for item in data['items']:
                            # Get product info to calculate item total
                            product_id = item.get("product_id")
                            quantity = item.get("quantity", 1)
                            
                            if product_id:
                                # This would need to query actual product prices from database
                                # For now, use a simple estimate or placeholder
                                cart_total += 50.0 * quantity  # Placeholder: $50 per item
                
                with db_manager.get_session() as session:
                    shipping_options = knowledge_base_service.get_shipping_options(
                        data.get('site_name', 'store1'), 
                        session, 
                        cart_total if cart_total > 0 else None
                    )
                
                # Calculate estimated total (cart + lowest shipping)
                lowest_shipping = 0.0
                for option in shipping_options:
                    if option['cost'] not in ["Calculated at checkout", "$0.00"]:
                        try:
                            cost_value = float(option['cost'].replace("$", "").replace(",", ""))
                            if lowest_shipping == 0.0 or cost_value < lowest_shipping:
                                lowest_shipping = cost_value
                        except ValueError:
                            continue
                
                estimated_total = f"${cart_total + lowest_shipping:.2f}" if cart_total > 0 else "TBD"
                
                result = {
                    "shipping_options": shipping_options[:3],
                    "total_cost": estimated_total
                }
                
                status, headers, response = json_response(result)
                start_response(status, headers)
                return response
                
            except Exception as e:
                status, headers, response = json_response(
                    {"error": "Error calculating shipping", "message": str(e)}, 
                    '500 Internal Server Error'
                )
                start_response(status, headers)
                return response
        
        # Default 404
        else:
            status, headers, response = json_response(
                {
                    "error": "Not Found",
                    "message": f"Endpoint {method} {path} not found",
                    "available_endpoints": [
                        "GET / - Health check",
                        "GET /ping - Simple ping test",
                        "GET /test-db - Database connection test",
                        "GET /db-schema - Database schema inspection",
                        "GET /check-models - Test all SQLAlchemy models",
                        "POST /chat - Main chat endpoint",
                        "POST /search/products - Product search",
                        "GET /sites - List all sites",
                        "GET /sites/{name}/stats - Site statistics",
                        "POST /shipping/calculate - Calculate shipping costs"
                    ]
                }, 
                '404 Not Found'
            )
            start_response(status, headers)
            return response
            
    except Exception as e:
        # Global error handler
        error_data = {
            "error": "Internal server error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        status, headers, response = json_response(error_data, '500 Internal Server Error')
        start_response(status, headers)
        return response

# cPanel expects this variable
app = application