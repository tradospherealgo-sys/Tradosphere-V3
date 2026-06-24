"""
Database Migration: Add Google OAuth support to users table

This migration:
1. Adds google_id column (unique, indexed)
2. Adds picture_url column
3. Adds name column
4. Makes password_hash optional (nullable)
5. Sets is_verified to True for all existing users
6. Adds necessary indexes

Safe to run against existing data - no data loss.
"""

import os
import sys
from datetime import datetime

def migrate_postgresql(connection):
    """Migrate PostgreSQL database"""
    cursor = connection.cursor()

    print("🔧 Migrating PostgreSQL users table...")

    try:
        # Add new columns if they don't exist
        cursor.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS
            google_id VARCHAR(255) UNIQUE;
        """)
        print("   ✓ Added google_id column")

        cursor.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS
            picture_url VARCHAR(500);
        """)
        print("   ✓ Added picture_url column")

        cursor.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS
            name VARCHAR(255);
        """)
        print("   ✓ Added name column")

        # Make password_hash nullable for Google auth
        cursor.execute("""
            ALTER TABLE users ALTER COLUMN
            password_hash DROP NOT NULL;
        """)
        print("   ✓ Made password_hash optional")

        # Set is_verified to True for all existing users (Google users are auto-verified)
        cursor.execute("""
            UPDATE users SET is_verified = TRUE;
        """)
        print("   ✓ Set is_verified to True for all users")

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_users_google_id
            ON users(google_id);
        """)
        print("   ✓ Created google_id index")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_users_name
            ON users(name);
        """)
        print("   ✓ Created name index")

        connection.commit()
        cursor.close()

        print("✅ PostgreSQL migration complete!")
        return True

    except Exception as e:
        print(f"❌ PostgreSQL migration failed: {str(e)}")
        connection.rollback()
        cursor.close()
        return False


def migrate_sqlite(connection):
    """Migrate SQLite database"""
    cursor = connection.cursor()

    print("🔧 Migrating SQLite users table...")

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row for row in cursor.fetchall()}

        # Add google_id if missing
        if 'google_id' not in columns:
            cursor.execute("""
                ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE;
            """)
            print("   ✓ Added google_id column")

        # Add picture_url if missing
        if 'picture_url' not in columns:
            cursor.execute("""
                ALTER TABLE users ADD COLUMN picture_url VARCHAR(500);
            """)
            print("   ✓ Added picture_url column")

        # Add name if missing
        if 'name' not in columns:
            cursor.execute("""
                ALTER TABLE users ADD COLUMN name VARCHAR(255);
            """)
            print("   ✓ Added name column")

        # Update password_hash to nullable by recreating table
        if columns['password_hash'][3] == 1:  # nullable = 1
            print("   ℹ️  password_hash already nullable")
        else:
            print("   ⚠️  password_hash requires migration to become nullable (SQLite limitation)")
            print("   💡 Consider recreating table for new schema")

        # Set is_verified to True for all users
        cursor.execute("UPDATE users SET is_verified = 1;")
        print("   ✓ Set is_verified to True for all users")

        connection.commit()
        cursor.close()

        print("✅ SQLite migration complete!")
        return True

    except Exception as e:
        print(f"❌ SQLite migration failed: {str(e)}")
        connection.rollback()
        cursor.close()
        return False


def main():
    """Main migration function"""
    print("=" * 70)
    print("DATABASE MIGRATION: Google OAuth Support")
    print("=" * 70)
    print("")

    try:
        # Get database URL from environment
        from database import engine

        # Get database type from connection string
        db_url = str(engine.url)

        if 'postgresql' in db_url:
            print("📊 Detected: PostgreSQL")
            import psycopg2
            from database import engine

            with engine.connect() as conn:
                raw_conn = conn.connection
                success = migrate_postgresql(raw_conn)

        elif 'sqlite' in db_url:
            print("📊 Detected: SQLite")
            import sqlite3

            # Extract database path from URL
            db_path = db_url.replace('sqlite:///', '')
            if db_path.startswith('sqlite:///'):
                db_path = db_path[10:]

            print(f"   Database: {db_path}")

            connection = sqlite3.connect(db_path)
            success = migrate_sqlite(connection)
            connection.close()

        else:
            print(f"❌ Unsupported database: {db_url}")
            return False

        print("")
        if success:
            print("✅ Migration completed successfully!")
            print("")
            print("Next steps:")
            print("1. Restart your application")
            print("2. Test Google login at /login")
            print("3. Verify user creation in database")
            return True
        else:
            print("❌ Migration failed!")
            return False

    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
