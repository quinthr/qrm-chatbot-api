import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .db_models import Base, Product, Category, Site, ShippingZone, ShippingMethod
from .config import config


class DatabaseManager:
    def __init__(self):
        # SQL Database
        self.engine = create_engine(config.database.url)
        # Don't create tables - they should already exist from the crawler
        # Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # ChromaDB disabled for hosting compatibility
        self.chroma_client = None
        self.embedding_function = None
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_products_collection(self, site_name: str):
        """ChromaDB disabled - return None"""
        return None
    
    def get_pages_collection(self, site_name: str):
        """ChromaDB disabled - return None"""
        return None
    
    def search_products(self, site_name: str, query: str, limit: int = 10):
        """Fallback product search using SQL LIKE instead of vector similarity"""
        try:
            with self.get_session() as session:
                site = session.query(Site).filter_by(name=site_name).first()
                if not site:
                    return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
                
                # Simple text search on product names and descriptions
                products = session.query(Product).filter(
                    Product.site_id == site.id,
                    (Product.name.ilike(f"%{query}%") | 
                     Product.description.ilike(f"%{query}%") |
                     Product.short_description.ilike(f"%{query}%"))
                ).limit(limit).all()
                
                # Format results to match ChromaDB structure
                ids = [[str(p.woo_id) for p in products]]
                documents = [[p.name for p in products]]
                metadatas = [[{"product_id": p.woo_id} for p in products]]
                distances = [[0.5 for _ in products]]  # Dummy distances
                
                return {"ids": ids, "documents": documents, "metadatas": metadatas, "distances": distances}
        except Exception as e:
            print(f"Error searching products: {e}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """Dependency for FastAPI"""
    with db_manager.get_session() as session:
        yield session