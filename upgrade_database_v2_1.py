#!/usr/bin/env python3
"""
Upgrade database schema to v2.1
Adds file_hash column to sources table for duplicate detection
"""

import psycopg2

POSTGRES_HOST = "srv778971.hstgr.cloud"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

def upgrade_database():
    """Add file_hash column to sources table."""
    print("🔄 Upgrading database to v2.1...")

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS
    )

    cur = conn.cursor()

    try:
        # Check if column already exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='sources' AND column_name='file_hash'
        """)

        if cur.fetchone():
            print("  ℹ️  Column file_hash already exists, skipping...")
        else:
            # Add file_hash column
            print("  ➕ Adding file_hash column to sources table...")
            cur.execute("""
                ALTER TABLE sources
                ADD COLUMN file_hash VARCHAR(32) UNIQUE
            """)

            # Add index for faster lookups
            print("  🔍 Creating index on file_hash...")
            cur.execute("""
                CREATE INDEX idx_sources_file_hash ON sources(file_hash)
            """)

            conn.commit()
            print("✅ Database upgraded successfully to v2.1!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    upgrade_database()
