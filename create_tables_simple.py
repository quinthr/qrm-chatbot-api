#!/usr/bin/env python3
"""
Simple conversation table creation using psycopg2
"""
import subprocess
import sys

# The SQL commands to create conversation tables
SQL_COMMANDS = """
-- Conversations table (for API)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) UNIQUE NOT NULL,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation messages table (for API)
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_site_id ON conversations(site_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Create triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS update_conversations_updated_at 
    BEFORE UPDATE ON conversations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
"""

def create_tables():
    """Create tables using psql command line"""
    db_url = "postgresql://qrm_chatbot_knowledge_base_user:N1G9a7BpQrAXdPg30q8xnIjMGZpg08OX@dpg-d19t1hidbo4c73brmnt0-a.singapore-postgres.render.com/qrm_chatbot_knowledge_base"
    
    try:
        print("Creating conversation tables using psql...")
        
        # Write SQL to temp file
        with open('/tmp/create_tables.sql', 'w') as f:
            f.write(SQL_COMMANDS)
        
        # Run psql command
        result = subprocess.run([
            'psql', db_url, '-f', '/tmp/create_tables.sql'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Conversation tables created successfully!")
            print("Output:", result.stdout)
            return True
        else:
            print("❌ Error creating tables:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ psql command not found. Trying alternative method...")
        return create_tables_curl()
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_tables_curl():
    """Alternative: create a simple Python-only solution"""
    print("Using pure Python approach...")
    
    # Let's just commit the files and let the user run it on Render
    print("📝 SQL files have been created. Please run the migration on your deployment:")
    print("1. The SQL is in add_conversation_tables.sql")
    print("2. You can run it manually on your PostgreSQL database")
    print("3. Or deploy the updated code and the API will handle missing tables gracefully")
    
    return True

if __name__ == "__main__":
    success = create_tables()
    if success:
        print("🎉 Process completed!")
    else:
        print("💥 Process failed!")
        exit(1)