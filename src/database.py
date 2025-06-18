import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .db_models import Base, Product, Category, Site, ShippingZone, ShippingMethod
from .config import config


class DatabaseManager:
    def __init__(self):
        # SQL Database with connection pooling settings
        self.engine = create_engine(
            config.database.url,
            pool_pre_ping=True,  # Verify connections before using them
            pool_recycle=3600,   # Recycle connections after 1 hour
            pool_size=10,        # Number of connections to maintain in pool
            max_overflow=20      # Maximum overflow connections
        )
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
        """Enhanced product search using SQL with multiple search strategies"""
        try:
            with self.get_session() as session:
                site = session.query(Site).filter_by(name=site_name).first()
                if not site:
                    return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
                
                # Split query into words for better matching
                query_words = query.lower().split()
                
                # Build comprehensive search conditions
                search_conditions = []
                
                for word in query_words:
                    word_pattern = f"%{word}%"
                    search_conditions.extend([
                        Product.name.ilike(word_pattern),
                        Product.description.ilike(word_pattern),
                        Product.short_description.ilike(word_pattern),
                        Product.sku.ilike(word_pattern),
                        Product.shipping_class.ilike(word_pattern)
                    ])
                
                # Also search full query
                full_query_pattern = f"%{query}%"
                search_conditions.extend([
                    Product.name.ilike(full_query_pattern),
                    Product.description.ilike(full_query_pattern),
                    Product.short_description.ilike(full_query_pattern)
                ])
                
                # Combine all conditions with OR
                from sqlalchemy import or_
                combined_condition = or_(*search_conditions)
                
                # Execute search with relevance scoring (approximate)
                products = session.query(Product).filter(
                    Product.site_id == site.id,
                    combined_condition
                ).limit(limit * 2).all()  # Get more results for ranking
                
                # Simple relevance scoring based on where matches occur
                scored_products = []
                for product in products:
                    score = 0
                    text_fields = [
                        (product.name or '', 3),  # Name matches are most important
                        (product.short_description or '', 2),
                        (product.description or '', 1),
                        (product.sku or '', 2)
                    ]
                    
                    for text, weight in text_fields:
                        text_lower = text.lower()
                        # Exact phrase match
                        if query.lower() in text_lower:
                            score += weight * 10
                        # Individual word matches
                        for word in query_words:
                            if word in text_lower:
                                score += weight
                    
                    scored_products.append((product, score))
                
                # Sort by score and limit results
                scored_products.sort(key=lambda x: x[1], reverse=True)
                final_products = [p[0] for p in scored_products[:limit]]
                
                # Format results to match ChromaDB structure
                ids = [[str(p.woo_id) for p in final_products]]
                documents = [[p.name for p in final_products]]
                metadatas = [[{"product_id": p.woo_id} for p in final_products]]
                distances = [[0.1 + (i * 0.1) for i in range(len(final_products))]]  # Simulated relevance scores
                
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