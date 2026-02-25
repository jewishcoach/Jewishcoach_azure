"""
Pytest configuration - set test database before any app imports.
"""
import os

# Use in-memory SQLite for tests (must be set before app imports)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
