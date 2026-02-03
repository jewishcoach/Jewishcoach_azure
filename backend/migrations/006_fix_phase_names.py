"""
Migration to update phase names from old format (Situation, Gap, etc.) to new format (S0, S1, etc.)
"""

from sqlalchemy import text
from app.database import engine

def upgrade():
    """Update existing phase names to match BSD methodology"""
    with engine.connect() as conn:
        # Update conversations table - change default phase name
        conn.execute(text("""
            UPDATE conversations 
            SET current_phase = 'S0' 
            WHERE current_phase = 'Situation' OR current_phase IS NULL
        """))
        
        # Map old phase names to new ones (if any exist)
        phase_mapping = {
            'Situation': 'S0',
            'Gap': 'S6',
            'Pattern': 'S7',
            'Paradigm': 'S7',
            'Stance': 'S8',
            'KMZ': 'S9',
            'New_Choice': 'S10',
            'Vision': 'S10',
            'PPD': 'S10',
        }
        
        for old_name, new_name in phase_mapping.items():
            conn.execute(text(f"""
                UPDATE conversations 
                SET current_phase = '{new_name}' 
                WHERE current_phase = '{old_name}'
            """))
        
        conn.commit()
        print("✅ Phase names updated successfully")

def downgrade():
    """Revert phase names to old format"""
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE conversations 
            SET current_phase = 'Situation' 
            WHERE current_phase = 'S0'
        """))
        conn.commit()
        print("✅ Phase names reverted to old format")

if __name__ == "__main__":
    print("Running migration: Fix phase names...")
    upgrade()
    print("Migration complete!")


