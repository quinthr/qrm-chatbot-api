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
        models_info = {
            "tables": {},
            "relationships": {},
            "total_tables": 0
        }
        
        async with db.get_session() as session:
            # Get table information using SQL queries
            tables_result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            table_names = [row[0] for row in tables_result.fetchall()]
            models_info["total_tables"] = len(table_names)
            
            for table_name in table_names:
                # Get columns
                columns_result = await session.execute(text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                    ORDER BY ordinal_position
                """), {"table_name": table_name})
                
                columns = []
                for col in columns_result.fetchall():
                    column_info = {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "default": col[3],
                        "max_length": col[4],
                        "numeric_precision": col[5],
                        "numeric_scale": col[6]
                    }
                    # Check if it's an auto-increment column
                    if col[3] and "nextval" in str(col[3]):
                        column_info["autoincrement"] = True
                    columns.append(column_info)
                
                # Get primary keys
                pk_result = await session.execute(text("""
                    SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                    AND constraint_name = (
                        SELECT constraint_name
                        FROM information_schema.table_constraints
                        WHERE table_schema = 'public'
                        AND table_name = :table_name
                        AND constraint_type = 'PRIMARY KEY'
                    )
                    ORDER BY ordinal_position
                """), {"table_name": table_name})
                primary_keys = [row[0] for row in pk_result.fetchall()]
                
                # Get foreign keys
                fk_result = await session.execute(text("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                    AND tc.table_name = :table_name
                """), {"table_name": table_name})
                
                foreign_keys = []
                for fk in fk_result.fetchall():
                    foreign_keys.append({
                        "constrained_columns": [fk[0]],
                        "referred_table": fk[1],
                        "referred_columns": [fk[2]]
                    })
                
                # Get indexes
                idx_result = await session.execute(text("""
                    SELECT
                        i.relname AS index_name,
                        a.attname AS column_name,
                        ix.indisunique AS is_unique
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    WHERE t.relkind = 'r'
                    AND t.relname = :table_name
                    AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                    ORDER BY i.relname, a.attnum
                """), {"table_name": table_name})
                
                # Group indexes by name
                indexes_dict = {}
                for idx in idx_result.fetchall():
                    idx_name = idx[0]
                    if idx_name not in indexes_dict:
                        indexes_dict[idx_name] = {
                            "name": idx_name,
                            "columns": [],
                            "unique": idx[2]
                        }
                    indexes_dict[idx_name]["columns"].append(idx[1])
                
                models_info["tables"][table_name] = {
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "indexes": list(indexes_dict.values())
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