#!/usr/bin/env python3
"""
Test database connection locally
"""
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_mysql_connection():
    """Test MySQL connection"""
    print("Testing MySQL connection...")
    
    try:
        from src.database_async import Database
        
        db = Database()
        await db._init_mysql()
        
        if db.async_session:
            print("✅ MySQL connection successful!")
            
            # Test a simple query
            async with db.get_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                print(f"✅ Query test successful: {row[0]}")
                
            # Test table access
            async with db.get_session() as session:
                result = await session.execute(text("SHOW TABLES"))
                tables = result.fetchall()
                print(f"✅ Found {len(tables)} tables in database")
                for table in tables[:5]:  # Show first 5 tables
                    print(f"   - {table[0]}")
                    
        else:
            print("❌ MySQL connection failed - no session created")
            
        await db.close()
        
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        import traceback
        traceback.print_exc()

def test_sync_mysql_connection():
    """Test MySQL connection with sync pymysql"""
    print("\nTesting sync MySQL connection...")
    
    try:
        import pymysql
        from src.config_modern import settings
        
        # Parse connection URL
        url = settings.database_url
        # Extract parts: mysql+pymysql://user:pass@host:port/db
        parts = url.replace("mysql+pymysql://", "").split("/")
        db_name = parts[1].split("?")[0]
        auth_host = parts[0].split("@")
        user_pass = auth_host[0].split(":")
        host_port = auth_host[1].split(":")
        
        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = int(host_port[1])
        
        print(f"Connecting to: {user}@{host}:{port}/{db_name}")
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            charset='utf8mb4',
            connect_timeout=10
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"✅ Sync MySQL connection successful: {result[0]}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} tables")
            
        connection.close()
        
    except Exception as e:
        print(f"❌ Sync MySQL connection failed: {e}")

async def test_chromadb():
    """Test ChromaDB connection"""
    print("\nTesting ChromaDB connection...")
    
    try:
        import chromadb
        from src.config_modern import settings
        
        if settings.chroma_persist_directory:
            print(f"Using persistent directory: {settings.chroma_persist_directory}")
            client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
        else:
            print("Using in-memory ChromaDB")
            client = chromadb.Client()
            
        collections = client.list_collections()
        print(f"✅ ChromaDB connection successful!")
        print(f"✅ Found {len(collections)} collections")
        
        for collection in collections:
            print(f"   - {collection.name}")
            
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")

async def main():
    """Run all tests"""
    print("🔍 Testing database connections...\n")
    
    # Test sync connection first (simpler)
    test_sync_mysql_connection()
    
    # Test async connection
    await test_mysql_connection()
    
    # Test ChromaDB
    await test_chromadb()
    
    print("\n✅ Database connection tests completed!")

if __name__ == "__main__":
    asyncio.run(main())