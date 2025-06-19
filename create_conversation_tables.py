#!/usr/bin/env python3
"""
Create missing conversation tables in PostgreSQL database
"""
import asyncio
import asyncpg
import os
from pathlib import Path

# Database URL from environment
DATABASE_URL = "postgresql://qrm_chatbot_knowledge_base_user:N1G9a7BpQrAXdPg30q8xnIjMGZpg08OX@dpg-d19t1hidbo4c73brmnt0-a.singapore-postgres.render.com/qrm_chatbot_knowledge_base"

async def create_tables():
    """Create conversation tables"""
    print("Connecting to PostgreSQL database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Read SQL file
        sql_file = Path(__file__).parent / "add_conversation_tables.sql"
        with open(sql_file, 'r') as f:
            sql_commands = f.read()
        
        print("Creating conversation tables...")
        
        # Execute SQL commands
        await conn.execute(sql_commands)
        
        print("✅ Conversation tables created successfully!")
        
        # Verify tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('conversations', 'conversation_messages')
            ORDER BY table_name
        """)
        
        print(f"✅ Verified tables: {[t['table_name'] for t in tables]}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(create_tables())
    if success:
        print("🎉 Database migration completed successfully!")
    else:
        print("💥 Database migration failed!")
        exit(1)