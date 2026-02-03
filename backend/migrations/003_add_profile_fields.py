"""
Migration: Add profile fields (display_name, gender) to users table
Run with: python -m migrations.003_add_profile_fields
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
engine = create_engine(DATABASE_URL)


def upgrade():
    """Add profile fields to users table"""
    with engine.connect() as conn:
        # Add display_name column
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN display_name VARCHAR
            """))
            print("✓ Added display_name column to users")
        except Exception as e:
            print(f"⚠ display_name column might already exist: {e}")
        
        # Add gender column
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN gender VARCHAR
            """))
            print("✓ Added gender column to users")
        except Exception as e:
            print(f"⚠ gender column might already exist: {e}")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    print("🚀 Running profile fields migration...")
    upgrade()



