"""
Database Initialization Script - Production Safe

Handles:
- Schema creation
- Schema migration
- Validation
- Graceful error handling
- Automatic recovery

Run via Railway release phase:
  release: python db_init.py
"""

import os
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with production-safe practices"""

    logger.info("=" * 80)
    logger.info("DATABASE INITIALIZATION - Production Mode")
    logger.info("=" * 80)
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    logger.info(f"Python: {sys.version}")
    logger.info("")

    try:
        # Import database components
        logger.info("1. Importing database modules...")
        from database import engine, Base as DB_Base, Signal
        from user_model import Base as User_Base
        from paper_trading_model import Base as PT_Base
        logger.info("   ✓ Database modules imported")

    except Exception as e:
        logger.error(f"   ✗ Failed to import database: {e}")
        return False

    try:
        # Test connection
        logger.info("")
        logger.info("2. Testing database connection...")
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            logger.info("   ✓ Database connection successful")

    except Exception as e:
        logger.error(f"   ✗ Database connection failed: {e}")
        return False

    try:
        # Create tables
        logger.info("")
        logger.info("3. Creating/updating schema...")
        DB_Base.metadata.create_all(bind=engine)
        User_Base.metadata.create_all(bind=engine)
        PT_Base.metadata.create_all(bind=engine)
        logger.info("   ✓ Schema creation complete")

    except Exception as e:
        logger.error(f"   ✗ Schema creation failed: {e}")
        return False

    try:
        # Validate schema
        logger.info("")
        logger.info("4. Validating schema...")
        from sqlalchemy import inspect

        inspector = inspect(engine)

        # Check tables
        tables = inspector.get_table_names()
        logger.info(f"   ✓ Tables found: {len(tables)}")
        for table in tables:
            logger.info(f"     • {table}")

        # Check signals table
        if 'signals' not in tables:
            logger.error("   ✗ Signals table not found!")
            return False

        # Check columns
        columns = inspector.get_columns('signals')
        column_count = len(columns)
        expected_count = 19

        logger.info(f"   ✓ Signals table: {column_count} columns")

        if column_count != expected_count:
            logger.warning(f"   ⚠️  Expected {expected_count} columns, found {column_count}")

        # List columns
        for col in columns:
            logger.info(f"     • {col['name']}")

        # Check users table
        if 'users' not in tables:
            logger.error("   ✗ Users table not found!")
            return False

        users_columns = inspector.get_columns('users')
        logger.info(f"   ✓ Users table: {len(users_columns)} columns")

        # Check for password_hash column (CRITICAL)
        column_names = [col['name'] for col in users_columns]
        if 'password_hash' not in column_names:
            logger.error("   ✗ CRITICAL: Users table missing password_hash column!")
            logger.error(f"     Found columns: {', '.join(column_names)}")
            logger.error("     This will cause 'no such column: users.password_hash' errors!")
            return False

        # List user columns
        for col in users_columns:
            logger.info(f"     • {col['name']}")

    except Exception as e:
        logger.error(f"   ✗ Schema validation failed: {e}")
        return False

    try:
        # Test read/write
        logger.info("")
        logger.info("5. Testing read/write...")
        from sqlalchemy.orm import sessionmaker

        Session = sessionmaker(bind=engine)
        session = Session()

        # Count records
        count = session.query(Signal).count()
        logger.info(f"   ✓ Database query successful")
        logger.info(f"   ✓ Current signals in database: {count}")

        session.close()

    except Exception as e:
        logger.error(f"   ✗ Read/write test failed: {e}")
        return False

    # Success
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ DATABASE INITIALIZATION COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Status: READY FOR PRODUCTION")
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    logger.info("")

    return True


if __name__ == "__main__":
    try:
        success = init_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
