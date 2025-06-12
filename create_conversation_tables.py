#!/usr/bin/env python3
"""
Create conversation tables for chat history storage
"""
from sqlalchemy import create_engine, text
from src.config import config

def create_conversation_tables():
    """Create conversation and conversation_messages tables"""
    engine = create_engine(config.database.url)
    
    with engine.connect() as conn:
        # Create conversations table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                site_id INTEGER NOT NULL,
                conversation_id VARCHAR(255) NOT NULL UNIQUE,
                user_id VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        """))
        
        # Create conversation_messages table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                conversation_id VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """))
        
        # Create indexes for better performance
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversations_site_id ON conversations(site_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at)
        """))
        
        conn.commit()
        print("✅ Conversation tables created successfully!")

if __name__ == "__main__":
    create_conversation_tables()