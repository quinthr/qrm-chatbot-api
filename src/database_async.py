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
        # Initialize PostgreSQL
        await self._init_postgresql()
        
        # Initialize ChromaDB
        await self._init_chromadb()
        
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        try:
            # Ensure we have a PostgreSQL URL
            db_url = settings.database_url
            if "mysql" in db_url:
                # Convert MySQL URL to PostgreSQL format
                db_url = db_url.replace("mysql+pymysql://", "postgresql+asyncpg://")
            elif "postgresql://" in db_url:
                # Convert sync URL to async
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            elif not "postgresql+asyncpg://" in db_url:
                # Assume it's already correct or needs asyncpg
                if "postgresql" not in db_url:
                    raise ValueError(f"Invalid database URL format: {db_url}")
            
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
                logger.info("PostgreSQL connection initialized successfully")
            except Exception as conn_err:
                logger.warning(f"PostgreSQL connection test failed: {conn_err}")
                # Continue without raising - allow graceful degradation
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            # Don't raise - allow app to start without database
            self.engine = None
            self.async_session = None
    
    async def _init_chromadb(self):
        """Initialize ChromaDB connection"""
        try:
            if settings.chroma_persist_directory:
                # Persistent ChromaDB
                self.chroma_client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            else:
                # In-memory ChromaDB for testing
                self.chroma_client = chromadb.Client(
                    settings=Settings(
                        anonymized_telemetry=False,
                        is_persistent=False
                    )
                )
            
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            # Don't raise - ChromaDB is optional
    
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
        """Get or create ChromaDB collection"""
        if not self.chroma_client:
            raise RuntimeError("ChromaDB not initialized")
            
        try:
            return self.chroma_client.get_collection(name)
        except:
            return self.chroma_client.create_collection(name)
    
    async def search_vectors(
        self, 
        collection_name: str,
        query_embedding: List[float],
        filter_dict: Optional[Dict] = None,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """Search vectors in ChromaDB collection"""
        if not self.chroma_client:
            return {"ids": [[]], "metadatas": [[]], "distances": [[]]}
        
        try:
            collection = self.get_collection(collection_name)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                where=filter_dict,
                n_results=n_results
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return {"ids": [[]], "metadatas": [[]], "distances": [[]]}
    
    async def close(self):
        """Close all database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("MySQL connection closed")
        
        # ChromaDB doesn't need explicit closing
        logger.info("Database connections closed")