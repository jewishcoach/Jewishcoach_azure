"""
Migration: Add LLM Judge & RBAC System
Date: 2026-01-14
Description: 
- Add is_admin column to users table
- Create conversation_flags table for quality auditing
"""

import sqlite3
import os
from pathlib import Path

def run_migration():
    # Get database path
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "coaching.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("Creating new database with all tables...")
        # If no database exists, just create all tables from models
        from app.database import engine, Base
        from app.models import User, Conversation, Message, Feedback, JournalEntry, ToolResponse, ConversationFlag
        Base.metadata.create_all(bind=engine)
        print("✅ Database created with all tables")
        return
    
    print(f"Running migration on: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if is_admin column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_admin' in columns:
            print("✅ is_admin column already exists in users table")
        else:
            print("📝 Adding is_admin column to users table...")
            cursor.execute("""
                ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL
            """)
            print("✅ Added is_admin column to users table")
        
        # Check if conversation_flags table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_flags'")
        if cursor.fetchone():
            print("✅ conversation_flags table already exists")
        else:
            print("📝 Creating conversation_flags table...")
            cursor.execute("""
                CREATE TABLE conversation_flags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    stage VARCHAR NOT NULL,
                    issue_type VARCHAR NOT NULL,
                    reasoning TEXT NOT NULL,
                    severity VARCHAR NOT NULL,
                    is_resolved BOOLEAN DEFAULT 0 NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            """)
            print("✅ Created conversation_flags table")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()




