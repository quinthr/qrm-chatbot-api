"""
Async database management with SQLAlchemy and ChromaDB
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, List, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
import chromadb
from chromadb.config import Settings

from .config_modern import settings

logger = logging.getLogger(__name__)

class Database:
    """Async database manager for MySQL and ChromaDB"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.chroma_client = None
        
    async def initialize(self):
        """Initialize database connections"""
        # Initialize Database (MySQL/SQLite)
        await self._init_database()
        
        # ChromaDB disabled for hosting compatibility (like sync version)
        logger.info("ChromaDB disabled for hosting compatibility - using SQL search")
        
    async def _init_database(self):
        """Initialize MySQL connection (async version)"""
        try:
            # Use MySQL with asyncmy driver
            db_url = settings.database_url
            if "mysql+pymysql://" in db_url:
                # Convert to async MySQL driver
                db_url = db_url.replace("mysql+pymysql://", "mysql+aiomysql://")
            elif "mysql://" in db_url:
                # Convert to async MySQL driver  
                db_url = db_url.replace("mysql://", "mysql+aiomysql://")
            elif "sqlite://" in db_url:
                # Keep SQLite as-is (can be async)
                db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
            
            self.engine = create_async_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=settings.debug
            )
            
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection with timeout
            try:
                async with self.engine.begin() as conn:
                    from sqlalchemy import text
                    await conn.execute(text("SELECT 1"))
                logger.info("Database connection initialized successfully")
            except Exception as conn_err:
                logger.warning(f"Database connection test failed: {conn_err}")
                # Continue without raising - allow graceful degradation
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Don't raise - allow app to start without database
            self.engine = None
            self.async_session = None
    
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session"""
        if not self.async_session:
            raise RuntimeError("Database not initialized")
            
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_collection(self, name: str):
        """ChromaDB disabled - return None"""
        return None
    
    async def search_vectors(
        self, 
        collection_name: str,
        query_embedding: List[float],
        filter_dict: Optional[Dict] = None,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """ChromaDB disabled - return empty results"""
        return {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    
    async def close(self):
        """Close all database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
        
        logger.info("Database connections closed")