import psycopg2

conn = psycopg2.connect(
    dbname="smartcourse_ai",
    user="smartcourse",
    password="password",
    host="127.0.0.1",
    port="5432"
)

cur = conn.cursor()

# Check tables
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
""")

tables = cur.fetchall()
print("Tables in smartcourse_ai:")
for table in tables:
    print(f"  - {table[0]}")

# Check alembic version
try:
    cur.execute("SELECT version_num FROM alembic_version")
    version = cur.fetchone()
    print(f"\nAlembic version: {version[0] if version else 'None'}")
except Exception as e:
    print(f"\nAlembic version: Not initialized ({e})")
    conn.rollback()

# Check if content_chunks exists
try:
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'content_chunks'
        )
    """)
    exists = cur.fetchone()[0]
    print(f"content_chunks exists: {exists}")
except Exception as e:
    print(f"Error checking content_chunks: {e}")
    conn.rollback()

# Check if chunk_embeddings exists
try:
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'chunk_embeddings'
        )
    """)
    exists = cur.fetchone()[0]
    print(f"chunk_embeddings exists: {exists}")
except Exception as e:
    print(f"Error checking chunk_embeddings: {e}")

cur.close()
conn.close()
