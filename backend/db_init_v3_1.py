#!/usr/bin/env python3
"""
Database initialization script for Tradosphere V3.1
Creates all tables from SQLAlchemy models
Usage: python backend/db_init_v3_1.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST.
# SECURITY (F-10): never load .env.development in production — see the same
# guard in tradosphere_saas_server_v3_1.py. Real prod secrets come from the
# platform's process environment.
if os.getenv('FLASK_ENV', '').lower() == 'production':
    load_dotenv()
else:
    env_file = Path(__file__).parent.parent / '.env.development'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def init_database():
    """Initialize database and create all tables"""
    try:
        from database_v3_1 import Base, engine, Session

        # Create all tables
        print("🔄 Creating database tables...")
        Base.metadata.create_all(engine)
        print("✅ Database tables created successfully")

        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📊 Tables created: {len(tables)}")
        for table in tables:
            print(f"   ✓ {table}")

        # F-22: demo-user creation removed. init_database() previously created
        # demo@tradosphere.com / DemoPass@2024 — a known, hardcoded credential
        # that would be injected into the production user table on any fresh DB,
        # giving anyone aware of it a valid login. Seed test accounts only via a
        # separate, FLASK_ENV-gated staging script, never in DB init.

        print("\n✅ Database initialization complete!")
        return True

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
