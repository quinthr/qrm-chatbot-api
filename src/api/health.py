"""Health check endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from typing import Dict, Any

from ..dependencies import get_db, get_services

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check"""
    return {"status": "healthy"}

@router.get("/health/detailed")
async def detailed_health_check(
    db = Depends(get_db),
    services = Depends(get_services)
) -> Dict[str, Any]:
    """Detailed health check with service status"""
    health_status = {
        "status": "healthy",
        "services": {
            "api": "operational",
            "mysql": "unknown",
            "chromadb": "unknown",
            "openai": "configured"
        }
    }
    
    # Check MySQL
    try:
        if db.async_session:
            async with db.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    health_status["services"]["mysql"] = "operational"
        else:
            health_status["services"]["mysql"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["mysql"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check ChromaDB
    try:
        if db.chroma_client:
            # Test collection access
            collections = await db.chroma_client.list_collections()
            health_status["services"]["chromadb"] = "operational"
            health_status["services"]["chromadb_collections"] = len(collections)
    except Exception as e:
        health_status["services"]["chromadb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status