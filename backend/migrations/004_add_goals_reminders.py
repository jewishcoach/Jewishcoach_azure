"""
Migration: Add coaching goals and reminders tables
"""
import sqlite3
from datetime import datetime

def upgrade(db_path='./coaching.db'):
    """Add coaching_goals and coaching_reminders tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create coaching_goals table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS coaching_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_type TEXT NOT NULL,  -- 'weekly', 'monthly', 'custom'
        title TEXT NOT NULL,
        description TEXT,
        target_count INTEGER,  -- e.g., "3 sessions per week"
        current_count INTEGER DEFAULT 0,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT DEFAULT 'active',  -- 'active', 'completed', 'cancelled'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')
    
    # Create coaching_reminders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS coaching_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        reminder_date TEXT NOT NULL,
        reminder_time TEXT,  -- HH:MM format
        repeat_type TEXT DEFAULT 'once',  -- 'once', 'daily', 'weekly', 'biweekly', 'monthly'
        repeat_days TEXT,  -- JSON array of weekday numbers [0-6] for weekly reminders
        is_active BOOLEAN DEFAULT 1,
        last_sent TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_goals_user ON coaching_goals(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_goals_dates ON coaching_goals(start_date, end_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_user ON coaching_reminders(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_date ON coaching_reminders(reminder_date)')
    
    conn.commit()
    conn.close()
    print("✅ Migration 004: Goals and Reminders tables created")


def downgrade(db_path='./coaching.db'):
    """Remove coaching_goals and coaching_reminders tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS coaching_reminders')
    cursor.execute('DROP TABLE IF EXISTS coaching_goals')
    
    conn.commit()
    conn.close()
    print("✅ Migration 004: Goals and Reminders tables removed")


if __name__ == '__main__':
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
    upgrade()



