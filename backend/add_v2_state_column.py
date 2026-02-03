"""
Add v2_state column to conversations table
"""
import sqlite3
import os
from pathlib import Path

# Find the database file
db_path = Path(__file__).parent / "coaching.db"

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    exit(1)

print(f"📊 Connecting to: {db_path}")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # Check if column exists
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'v2_state' in columns:
        print("✅ Column 'v2_state' already exists!")
    else:
        print("➕ Adding column 'v2_state'...")
        cursor.execute("ALTER TABLE conversations ADD COLUMN v2_state JSON")
        conn.commit()
        print("✅ Column added successfully!")
    
    # Verify
    cursor.execute("PRAGMA table_info(conversations)")
    columns = cursor.fetchall()
    print("\n📋 Conversations table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n✅ Migration complete!")
