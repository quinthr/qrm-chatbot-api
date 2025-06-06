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
    
    # Test ChromaDB connection
    try:
        collections = db_manager.chroma_client.list_collections()
        vector_db_connected = True
    except Exception:
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
            conversation_id=request.conversation_id
        )
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        if config.api.debug:
            traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
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
    """Calculate shipping costs (placeholder implementation)"""
    try:
        # This is a simplified implementation
        # In a real scenario, you'd integrate with WooCommerce shipping calculations
        
        with db_manager.get_session() as session:
            shipping_options = knowledge_base_service.get_shipping_options(request.site_name, session)
        
        # For now, return available shipping methods
        # You would implement actual cost calculation based on location and items
        
        return ShippingCalculateResponse(
            shipping_options=shipping_options[:3],
            total_cost="TBD"  # Would calculate based on items and location
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