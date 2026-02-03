"""
Migration: Add Workspace Features (Journal conversation_id & ToolResponse table)
Date: 2026-01-14
Description: 
- Add conversation_id and updated_at to journal_entries table
- Create tool_responses table for storing interactive tool submissions
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
        from app.models import User, Conversation, Message, Feedback, JournalEntry, ToolResponse
        Base.metadata.create_all(bind=engine)
        print("✅ Database created with all tables")
        return
    
    print(f"Running migration on: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(journal_entries)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'conversation_id' in columns:
            print("✅ Migration already applied (conversation_id exists)")
        else:
            print("📝 Applying migration...")
            
            # Step 1: Create new journal_entries table with correct schema
            cursor.execute("""
                CREATE TABLE journal_entries_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    conversation_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            
            # Step 2: Copy existing data (if any) - assign to first conversation of each user
            cursor.execute("""
                INSERT INTO journal_entries_new (id, user_id, conversation_id, content, created_at, updated_at)
                SELECT 
                    je.id, 
                    je.user_id, 
                    COALESCE(
                        (SELECT id FROM conversations WHERE user_id = je.user_id ORDER BY created_at ASC LIMIT 1),
                        1
                    ) as conversation_id,
                    je.content,
                    je.created_at,
                    je.created_at as updated_at
                FROM journal_entries je
            """)
            
            # Step 3: Drop old table and rename new one
            cursor.execute("DROP TABLE journal_entries")
            cursor.execute("ALTER TABLE journal_entries_new RENAME TO journal_entries")
            
            print("✅ Added conversation_id and updated_at to journal_entries")
        
        # Check if tool_responses table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_responses'")
        if cursor.fetchone():
            print("✅ tool_responses table already exists")
        else:
            # Create tool_responses table
            cursor.execute("""
                CREATE TABLE tool_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    tool_type VARCHAR NOT NULL,
                    data JSON NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            print("✅ Created tool_responses table")
        
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




