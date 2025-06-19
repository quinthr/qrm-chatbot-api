"""
Modern FastAPI application for QRM Chatbot API
Optimized for Render deployment with latest technologies
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional

from src.config_modern import settings
from src.database_async import Database
from src.services_async import ChatService, KnowledgeBaseService
from src.models_modern import (
    ChatRequest, ChatResponse,
    ProductSearchRequest, ProductSearchResponse,
    ShippingCalculateRequest, ShippingCalculateResponse
)
from src.api import chat, products, shipping, health

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db: Optional[Database] = None
kb_service: Optional[KnowledgeBaseService] = None
chat_service: Optional[ChatService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global db, kb_service, chat_service
    
    logger.info("Starting QRM Chatbot API...")
    
    # Initialize database
    db = Database()
    await db.initialize()
    
    # Initialize services
    kb_service = KnowledgeBaseService(db)
    chat_service = ChatService(db, kb_service)
    
    # Set services in app state for dependency injection
    app.state.db = db
    app.state.kb_service = kb_service
    app.state.chat_service = chat_service
    
    logger.info("API initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down QRM Chatbot API...")
    await db.close()

# Create FastAPI app
app = FastAPI(
    title="QRM Chatbot API",
    description="AI-powered customer support for WooCommerce sites",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(products.router, prefix="/api/v1", tags=["products"])
app.include_router(shipping.router, prefix="/api/v1", tags=["shipping"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "QRM Chatbot API",
        "version": "2.0.0",
        "status": "operational"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "status_code": 500
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )