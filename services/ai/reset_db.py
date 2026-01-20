import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to postgres database
conn = psycopg2.connect(
    dbname="postgres",
    user="smartcourse",
    password="password",
    host="127.0.0.1",
    port="5432"
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

# Terminate all connections to smartcourse_ai
print("Terminating connections to smartcourse_ai...")
cur.execute("""
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = 'smartcourse_ai'
    AND pid <> pg_backend_pid()
""")

# Drop and recreate smartcourse_ai database
print("Dropping smartcourse_ai database...")
cur.execute("DROP DATABASE IF EXISTS smartcourse_ai")
print("Creating smartcourse_ai database...")
cur.execute("CREATE DATABASE smartcourse_ai OWNER smartcourse")
print("Database reset complete!")

cur.close()
conn.close()
