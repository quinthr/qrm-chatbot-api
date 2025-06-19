"""Health check endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, inspect
from typing import Dict, Any, List
import logging

from ..dependencies import get_db, get_services

logger = logging.getLogger(__name__)
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
            "postgresql": "unknown", 
            "chromadb": "unknown",
            "openai": "configured"
        }
    }
    
    # Check PostgreSQL
    try:
        if db.async_session:
            async with db.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    health_status["services"]["postgresql"] = "operational"
        else:
            health_status["services"]["postgresql"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["postgresql"] = f"error: {str(e)}"
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

@router.get("/db-schema")
async def get_database_schema(db = Depends(get_db)) -> Dict[str, Any]:
    """Get complete database schema information"""
    if not db.async_session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        schema_info = {
            "tables": {},
            "total_tables": 0,
            "database_type": "postgresql" if "postgresql" in str(db.engine.url) else "other"
        }
        
        async with db.get_session() as session:
            # Get all tables
            tables_result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in tables_result.fetchall()]
            
            schema_info["total_tables"] = len(tables)
            
            # Get detailed info for each table
            for table_name in tables:
                # Get columns
                columns_result = await session.execute(text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                    ORDER BY ordinal_position
                """), {"table_name": table_name})
                
                columns = []
                for col in columns_result.fetchall():
                    columns.append({
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "default": col[3],
                        "max_length": col[4]
                    })
                
                # Get row count
                try:
                    count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    row_count = count_result.scalar()
                except:
                    row_count = "Error"
                
                schema_info["tables"][table_name] = {
                    "columns": columns,
                    "column_count": len(columns),
                    "row_count": row_count
                }
        
        return schema_info
        
    except Exception as e:
        logger.error(f"Error getting database schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")

@router.get("/sqlalchemy-models")
async def get_sqlalchemy_models(db = Depends(get_db)) -> Dict[str, Any]:
    """Get SQLAlchemy model definitions from the current database"""
    if not db.async_session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Import the models to get their definitions
        from ..services_async import KnowledgeBaseService
        
        async with db.get_session() as session:
            # Use SQLAlchemy inspector
            inspector = inspect(session.bind)
            
            models_info = {
                "tables": {},
                "relationships": {},
                "total_tables": 0
            }
            
            table_names = inspector.get_table_names()
            models_info["total_tables"] = len(table_names)
            
            for table_name in table_names:
                # Get columns with SQLAlchemy inspector
                columns = inspector.get_columns(table_name)
                primary_keys = inspector.get_pk_constraint(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)
                
                models_info["tables"][table_name] = {
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col["nullable"],
                            "default": str(col["default"]) if col["default"] is not None else None,
                            "autoincrement": col.get("autoincrement", False)
                        }
                        for col in columns
                    ],
                    "primary_keys": primary_keys["constrained_columns"] if primary_keys else [],
                    "foreign_keys": [
                        {
                            "constrained_columns": fk["constrained_columns"],
                            "referred_table": fk["referred_table"],
                            "referred_columns": fk["referred_columns"]
                        }
                        for fk in foreign_keys
                    ],
                    "indexes": [
                        {
                            "name": idx["name"],
                            "columns": idx["column_names"],
                            "unique": idx["unique"]
                        }
                        for idx in indexes
                    ]
                }
            
            return models_info
            
    except Exception as e:
        logger.error(f"Error getting SQLAlchemy models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@router.get("/sample-data/{table_name}")
async def get_sample_data(
    table_name: str,
    limit: int = 5,
    db = Depends(get_db)
) -> Dict[str, Any]:
    """Get sample data from a specific table"""
    if not db.async_session:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with db.get_session() as session:
            # Validate table exists
            table_check = await session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            """), {"table_name": table_name})
            
            if table_check.scalar() == 0:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            # Get sample data
            result = await session.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit'), {"limit": limit})
            rows = result.fetchall()
            columns = result.keys()
            
            sample_data = []
            for row in rows:
                sample_data.append(dict(zip(columns, row)))
            
            return {
                "table_name": table_name,
                "sample_count": len(sample_data),
                "total_limit": limit,
                "data": sample_data
            }
            
    except Exception as e:
        logger.error(f"Error getting sample data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sample data: {str(e)}")