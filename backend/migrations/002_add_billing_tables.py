"""
Migration: Add billing and subscription tables
Run with: python -m migrations.002_add_billing_tables
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")
engine = create_engine(DATABASE_URL)


def upgrade():
    """Add billing tables"""
    with engine.connect() as conn:
        # Add columns to users table
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN stripe_customer_id VARCHAR UNIQUE
            """))
            print("✓ Added stripe_customer_id to users")
        except Exception as e:
            print(f"⚠ stripe_customer_id column might already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN current_plan VARCHAR DEFAULT 'basic' NOT NULL
            """))
            print("✓ Added current_plan to users")
        except Exception as e:
            print(f"⚠ current_plan column might already exist: {e}")
        
        # Create subscriptions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                stripe_subscription_id VARCHAR UNIQUE,
                stripe_price_id VARCHAR,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                cancel_at_period_end BOOLEAN DEFAULT 0 NOT NULL,
                coupon_code VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        print("✓ Created subscriptions table")
        
        # Create usage_records table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                messages_used INTEGER DEFAULT 0 NOT NULL,
                speech_minutes_used INTEGER DEFAULT 0 NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        print("✓ Created usage_records table")
        
        # Create coupons table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR UNIQUE NOT NULL,
                plan_granted VARCHAR NOT NULL,
                duration_days INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0 NOT NULL,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                expires_at TIMESTAMP,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        print("✓ Created coupons table")
        
        # Create coupon_redemptions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS coupon_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coupon_id INTEGER NOT NULL,
                redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (coupon_id) REFERENCES coupons(id)
            )
        """))
        print("✓ Created coupon_redemptions table")
        
        # Insert BSD100 coupon
        conn.execute(text("""
            INSERT OR IGNORE INTO coupons 
            (code, plan_granted, duration_days, max_uses, is_active, description)
            VALUES 
            ('BSD100', 'pro', NULL, NULL, 1, 
             'BSD Special Launch Offer - Lifetime PRO access')
        """))
        print("✓ Inserted BSD100 coupon")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")


def downgrade():
    """Remove billing tables"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS coupon_redemptions"))
        conn.execute(text("DROP TABLE IF EXISTS coupons"))
        conn.execute(text("DROP TABLE IF EXISTS usage_records"))
        conn.execute(text("DROP TABLE IF EXISTS subscriptions"))
        # Note: Cannot easily drop columns in SQLite
        conn.commit()
        print("✅ Downgrade completed!")


if __name__ == "__main__":
    print("🚀 Running billing tables migration...")
    upgrade()



