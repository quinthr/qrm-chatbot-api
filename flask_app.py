#!/usr/bin/env python3
"""
Flask-based API for better WSGI compatibility
This is a simplified version of the FastAPI app
"""
from flask import Flask, request, jsonify
from datetime import datetime
import traceback

# Import our existing components
from src.config import config
from src.database import db_manager
from src.services import chat_service, knowledge_base_service

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    if config.api.debug:
        traceback.print_exc()
    
    return jsonify({
        "detail": "Internal server error",
        "error": str(e) if config.api.debug else "Something went wrong"
    }), 500


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with db_manager.get_session() as session:
            session.execute("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False
    
    # ChromaDB disabled for hosting compatibility
    vector_db_connected = False
    
    # Check OpenAI configuration
    openai_configured = bool(config.openai.api_key and config.openai.api_key != "")
    
    status_code = "healthy" if db_connected and openai_configured else "degraded"
    
    return jsonify({
        "status": status_code,
        "timestamp": datetime.utcnow().isoformat(),
        "database_connected": db_connected,
        "vector_db_connected": vector_db_connected,
        "openai_configured": openai_configured
    })


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Main chat endpoint for WordPress plugin"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'message' not in data or 'site_name' not in data:
            return jsonify({"detail": "Missing required fields: message, site_name"}), 400
        
        # Validate site
        with db_manager.get_session() as session:
            from src.db_models import Site
            site = session.query(Site).filter_by(name=data['site_name']).first()
            if not site:
                return jsonify({"detail": f"Site '{data['site_name']}' not found"}), 404
        
        # Generate response
        result = chat_service.generate_response(
            message=data['message'],
            site_name=data['site_name'],
            conversation_id=data.get('conversation_id')
        )
        
        return jsonify(result)
        
    except Exception as e:
        if config.api.debug:
            traceback.print_exc()
        return jsonify({"detail": f"Error processing chat request: {str(e)}"}), 500


@app.route('/search/products', methods=['POST'])
def search_products():
    """Search products endpoint"""
    try:
        data = request.get_json()
        
        if not data or 'site_name' not in data or 'query' not in data:
            return jsonify({"detail": "Missing required fields: site_name, query"}), 400
        
        products = knowledge_base_service.search_products(
            site_name=data['site_name'],
            query=data['query'],
            limit=data.get('limit', 10)
        )
        
        return jsonify({
            "products": products,
            "total_found": len(products)
        })
        
    except Exception as e:
        if config.api.debug:
            traceback.print_exc()
        return jsonify({"detail": f"Error searching products: {str(e)}"}), 500


@app.route('/sites', methods=['GET'])
def list_sites():
    """List available sites"""
    try:
        from src.db_models import Site
        with db_manager.get_session() as session:
            sites = session.query(Site).all()
            return jsonify([
                {
                    "name": site.name,
                    "url": site.url,
                    "is_active": site.is_active,
                    "created_at": site.created_at.isoformat() if site.created_at else None
                }
                for site in sites
            ])
    except Exception as e:
        return jsonify({"detail": f"Error listing sites: {str(e)}"}), 500


@app.route('/sites/<site_name>/stats', methods=['GET'])
def get_site_stats(site_name):
    """Get statistics for a specific site"""
    try:
        from src.db_models import Site, Product, Category
        
        with db_manager.get_session() as session:
            site = session.query(Site).filter_by(name=site_name).first()
            if not site:
                return jsonify({"detail": "Site not found"}), 404
            
            product_count = session.query(Product).filter_by(site_id=site.id).count()
            category_count = session.query(Category).filter_by(site_id=site.id).count()
            
            return jsonify({
                "site_name": site_name,
                "product_count": product_count,
                "category_count": category_count,
                "last_updated": site.updated_at.isoformat() if site.updated_at else None
            })
    except Exception as e:
        return jsonify({"detail": f"Error getting site stats: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(
        host=config.api.host,
        port=config.api.port,
        debug=config.api.debug
    )