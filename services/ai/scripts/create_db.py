"""Create AI service database."""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection parameters
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "smartcourse"
DB_PASSWORD = "password"
DB_NAME = "smartcourse_ai"

def create_ai_database():
    """Create the AI service database if it doesn't exist."""
    
    # Connect to PostgreSQL server
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"  # Connect to default database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (DB_NAME,)
        )
        
        if cursor.fetchone():
            print(f"Database '{DB_NAME}' already exists")
        else:
            # Create the database
            cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"Database '{DB_NAME}' created successfully")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        raise

if __name__ == "__main__":
    create_ai_database()
    print("AI service database setup complete!")