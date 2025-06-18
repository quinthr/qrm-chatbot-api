#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

from src.config import config
from src.database import get_db, db_manager
from src.models import (
    ChatRequest, ChatResponse, ProductSearchRequest, ProductSearchResponse,
    ShippingCalculateRequest, ShippingCalculateResponse, HealthResponse
)
from src.services import chat_service, knowledge_base_service

# Create FastAPI app
app = FastAPI(
    title="Mass Loaded Vinyl Chatbot API",
    description="AI-powered customer service chatbot for WooCommerce sites",
    version="1.0.0",
    docs_url="/docs" if config.api.debug else None,
    redoc_url="/redoc" if config.api.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    if config.api.debug:
        traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if config.api.debug else "Something went wrong"}
    )


@app.get("/test-db")
async def test_database():
    """Test database connection directly"""
    try:
        with db_manager.get_session() as session:
            # Simple query to test connection
            from src.db_models import Site
            count = session.query(Site).count()
            return {"status": "ok", "site_count": count}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc() if config.api.debug else None
            }
        )


@app.get("/db-schema")
async def get_database_schema():
    """Get all tables and columns in the database for troubleshooting"""
    try:
        from sqlalchemy import inspect, text
        
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
            
            return schema_info
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc() if config.api.debug else None
            }
        )


@app.get("/check-models")
async def check_models():
    """Check if all models can be queried successfully"""
    from src import db_models
    
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
    
    return {
        "summary": summary,
        "models": results
    }


@app.get("/", response_model=HealthResponse)
async def health_check():
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
    
    status_code = "healthy" if db_connected and vector_db_connected and openai_configured else "degraded"
    
    return HealthResponse(
        status=status_code,
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        vector_db_connected=vector_db_connected,
        openai_configured=openai_configured
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for WordPress plugin"""
    try:
        # Validate site
        with db_manager.get_session() as session:
            from src.db_models import Site
            site = session.query(Site).filter_by(name=request.site_name).first()
            if not site:
                raise HTTPException(
                    status_code=404,
                    detail=f"Site '{request.site_name}' not found"
                )
        
        # Generate response
        result = chat_service.generate_response(
            message=request.message,
            site_name=request.site_name,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        if config.api.debug:
            traceback.print_exc()
        
        # Extract the actual error from RetryError
        error_message = str(e)
        error_type = type(e).__name__
        
        # Try to extract the underlying error from RetryError
        if "RetryError" in str(type(e)):
            # Try multiple ways to get the underlying error
            underlying_error = None
            
            # Method 1: Check __cause__
            if hasattr(e, '__cause__') and e.__cause__:
                underlying_error = e.__cause__
            # Method 2: Check last_attempt
            elif hasattr(e, 'last_attempt') and hasattr(e.last_attempt, 'exception'):
                underlying_error = e.last_attempt.exception()
            # Method 3: Parse from string representation
            elif "raised" in str(e):
                import re
                match = re.search(r'raised (\w+)', str(e))
                if match:
                    error_type = match.group(1)
                    error_message = f"{error_type}: Database connection error - check logs for details"
            
            if underlying_error:
                error_type = type(underlying_error).__name__
                error_message = str(underlying_error)
        
        # Return detailed error information
        return JSONResponse(
            status_code=500,
            content={
                "error": "Chat service internal error",
                "error_type": error_type,
                "error_message": error_message,
                "traceback": traceback.format_exc() if config.api.debug else None
            }
        )


@app.post("/search/products", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest):
    """Search products endpoint"""
    try:
        products = knowledge_base_service.search_products(
            site_name=request.site_name,
            query=request.query,
            limit=request.limit
        )
        
        return ProductSearchResponse(
            products=products,
            total_found=len(products)
        )
        
    except Exception as e:
        if config.api.debug:
            traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error searching products: {str(e)}"
        )


@app.get("/sites")
async def list_sites(db: Session = Depends(get_db)):
    """List available sites"""
    try:
        from src.db_models import Site
        sites = db.query(Site).all()
        return [
            {
                "name": site.name,
                "url": site.url,
                "is_active": site.is_active,
                "created_at": site.created_at
            }
            for site in sites
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing sites: {str(e)}"
        )


@app.get("/sites/{site_name}/stats")
async def get_site_stats(site_name: str, db: Session = Depends(get_db)):
    """Get statistics for a specific site"""
    try:
        from src.db_models import Site, Product, Category
        
        site = db.query(Site).filter_by(name=site_name).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        product_count = db.query(Product).filter_by(site_id=site.id).count()
        category_count = db.query(Category).filter_by(site_id=site.id).count()
        
        return {
            "site_name": site_name,
            "product_count": product_count,
            "category_count": category_count,
            "last_updated": site.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting site stats: {str(e)}"
        )


@app.post("/shipping/calculate", response_model=ShippingCalculateResponse)
async def calculate_shipping(request: ShippingCalculateRequest):
    """Calculate shipping costs with actual cost calculations"""
    try:
        # Calculate cart total from items
        cart_total = 0.0
        if request.items:
            with db_manager.get_session() as session:
                for item in request.items:
                    # Get product info to calculate item total
                    product_id = item.get("product_id")
                    quantity = item.get("quantity", 1)
                    
                    if product_id:
                        # This would need to query actual product prices from database
                        # For now, use a simple estimate or placeholder
                        cart_total += 50.0 * quantity  # Placeholder: $50 per item
        
        with db_manager.get_session() as session:
            shipping_options = knowledge_base_service.get_shipping_options(
                request.site_name, 
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
        
        return ShippingCalculateResponse(
            shipping_options=shipping_options[:3],
            total_cost=estimated_total
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating shipping: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug
    )