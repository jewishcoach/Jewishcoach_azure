"""
Migration: coach_feedback_survey_submissions table
Run: cd backend && python migrations/007_add_coach_feedback_survey.py
"""
from sqlalchemy import create_engine, inspect as sa_inspect
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./coaching.db")

from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401


def upgrade():
    engine = create_engine(DATABASE_URL)
    insp = sa_inspect(engine)
    if "coach_feedback_survey_submissions" not in insp.get_table_names():
        Base.metadata.create_all(bind=engine, tables=[app.models.CoachFeedbackSurveySubmission.__table__])
        print("✓ Created coach_feedback_survey_submissions")
    else:
        print("✓ coach_feedback_survey_submissions already present")
    print("✅ Migration 007 done")


if __name__ == "__main__":
    upgrade()
