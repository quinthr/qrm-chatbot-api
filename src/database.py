import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import chromadb
from chromadb.utils import embedding_functions

# Add crawler path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../crawler/src"))

from models import Base, Product, Category, Site, ShippingZone, ShippingMethod
from config import config


class DatabaseManager:
    def __init__(self):
        # SQL Database
        self.engine = create_engine(config.database.url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # ChromaDB for vector search
        self.chroma_client = chromadb.PersistentClient(
            path=config.database.chroma_persist_directory
        )
        
        # OpenAI embeddings
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=config.openai.api_key,
            model_name="text-embedding-ada-002"
        )
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_products_collection(self, site_name: str):
        """Get ChromaDB collection for products"""
        collection_name = f"products_{site_name}"
        return self.chroma_client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
    
    def get_pages_collection(self, site_name: str):
        """Get ChromaDB collection for pages"""
        collection_name = f"pages_{site_name}"
        return self.chroma_client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
    
    def search_products(self, site_name: str, query: str, limit: int = 10):
        """Search products using vector similarity"""
        try:
            collection = self.get_products_collection(site_name)
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except Exception as e:
            print(f"Error searching products: {e}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """Dependency for FastAPI"""
    with db_manager.get_session() as session:
        yield session