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

# Load environment variables FIRST
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

        # Create demo user if it doesn't exist
        session = Session()
        try:
            from user_model_v3_1 import User
            from auth_manager_v3_1 import PasswordManager

            existing_user = session.query(User).filter_by(email="demo@tradosphere.com").first()
            if not existing_user:
                print("\n👤 Creating demo user...")
                demo_user = User(
                    email="demo@tradosphere.com",
                    username="demo",
                    password_hash=PasswordManager.hash_password("DemoPass@2024"),
                    is_active=True
                )
                session.add(demo_user)
                session.commit()
                print("✅ Demo user created (demo@tradosphere.com / DemoPass@2024)")
            else:
                print("✅ Demo user already exists")
        finally:
            session.close()

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
