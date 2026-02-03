"""
Migration: Add Google Calendar integration fields
"""
import sqlite3

def upgrade(db_path='./coaching.db'):
    """Add google_calendar_token to users table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add google calendar fields
    cursor.execute('''
    ALTER TABLE users
    ADD COLUMN google_calendar_token TEXT
    ''')
    
    cursor.execute('''
    ALTER TABLE users
    ADD COLUMN google_calendar_refresh_token TEXT
    ''')
    
    cursor.execute('''
    ALTER TABLE users
    ADD COLUMN google_calendar_synced_at TEXT
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Migration 005: Google Calendar fields added")


def downgrade(db_path='./coaching.db'):
    """Remove Google Calendar fields (SQLite doesn't support DROP COLUMN easily)"""
    print("⚠️  SQLite doesn't support DROP COLUMN - manual migration required")


if __name__ == '__main__':
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
    upgrade()



