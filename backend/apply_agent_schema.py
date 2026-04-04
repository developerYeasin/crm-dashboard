#!/usr/bin/env python3
"""
Simple database migration: Create autonomous agent framework tables.
This script uses raw SQL to avoid Flask app context issues.
"""

import sys
from pathlib import Path
import mysql.connector
from mysql.connector import Error

ROOT_DIR = Path(__file__).parent.absolute()
SCHEMA_FILE = ROOT_DIR / 'agent_framework' / 'schema.sql'

def read_schema():
    with open(SCHEMA_FILE, 'r') as f:
        return f.read()

def execute_schema(connection, schema_sql):
    cursor = connection.cursor()
    statements = schema_sql.split(';')
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
                print(f"✓ Executed: {stmt[:60]}...")
            except Error as e:
                # Ignore "table already exists" errors
                if e.errno == 1050:  # Table already exists
                    print(f"⊘ Table exists (skipping): {stmt[:60]}...")
                else:
                    print(f"✗ Error executing statement: {e}")
                    raise
    connection.commit()
    cursor.close()

def main():
    print("=" * 60)
    print("Agent Framework Database Migration")
    print("=" * 60)

    # Read config from environment or defaults
    import os
    from dotenv import load_dotenv

    # Load .env file if exists
    env_file = ROOT_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)

    db_config = {
        'host': os.getenv('DB_HOST', os.getenv('MYSQL_HOST', 'localhost')),
        'port': int(os.getenv('DB_PORT', os.getenv('MYSQL_PORT', 3306))),
        'user': os.getenv('DB_USER', os.getenv('MYSQL_USER', 'root')),
        'password': os.getenv('DB_PASSWORD', os.getenv('MYSQL_PASSWORD', '')),
        'database': os.getenv('DB_NAME', os.getenv('MYSQL_DB', 'order_tracker'))
    }

    print(f"\nConnecting to database: {db_config['database']} on {db_config['host']}")
    print(f"User: {db_config['user']}")

    try:
        connection = mysql.connector.connect(**db_config)
        print("✓ Connected to MySQL")

        schema_sql = read_schema()
        print(f"\nExecuting schema from: {SCHEMA_FILE}")
        print("-" * 60)

        execute_schema(connection, schema_sql)

        print("-" * 60)
        print("\n✅ Migration completed successfully!")

        # Verify tables
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'agent_%'")
        tables = cursor.fetchall()
        print(f"\nCreated/verified {len(tables)} agent tables:")
        for table in tables:
            print(f"  • {table[0]}")
        cursor.close()

        # Check if templates exist
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_templates")
        count = cursor.fetchone()[0]
        cursor.close()

        if count == 0:
            print("\nℹ️  No agent templates found. Run with --seed to add default templates.")
        else:
            print(f"\n✓ Found {count} agent templates in database.")

        connection.close()
        print("\n✅ Done!")

    except Error as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n✗ Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
