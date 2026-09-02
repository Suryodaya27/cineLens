#!/usr/bin/env python3
"""
Fix vector index for face embeddings.
The issue might be with the IVFFlat index not working properly.
"""

import psycopg2
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=os.getenv('POSTGRES_PORT', '5432'),
    database=os.getenv('POSTGRES_DB', 'face_recognition'),
    user=os.getenv('POSTGRES_USER', 'postgres'),
    password=os.getenv('POSTGRES_PASSWORD', 'postgres')
)

cur = conn.cursor()

print("Checking current indexes...")
cur.execute("""
    SELECT indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename = 'face_embeddings';
""")

indexes = cur.fetchall()
print(f"Found {len(indexes)} indexes:")
for name, definition in indexes:
    print(f"  • {name}")
    print(f"    {definition}")

# Drop the existing vector index
print("\nDropping existing vector index...")
try:
    cur.execute("DROP INDEX IF EXISTS face_embeddings_vector_idx;")
    conn.commit()
    print("✓ Dropped old index")
except Exception as e:
    print(f"⚠️  Error dropping index: {e}")
    conn.rollback()

# Check number of embeddings
cur.execute("SELECT COUNT(*) FROM face_embeddings;")
count = cur.fetchone()[0]
print(f"\nTotal embeddings: {count}")

# Create a simpler index for small datasets
# IVFFlat is for large datasets (>10k rows), for small datasets use HNSW or no index
if count < 100:
    print("\nSmall dataset detected. Using HNSW index (better for small datasets)...")
    try:
        cur.execute("""
            CREATE INDEX face_embeddings_vector_idx 
            ON face_embeddings 
            USING hnsw (embedding vector_cosine_ops);
        """)
        conn.commit()
        print("✓ Created HNSW index")
    except Exception as e:
        print(f"⚠️  HNSW not available, trying without index: {e}")
        conn.rollback()
        print("   Queries will use sequential scan (slower but works)")
else:
    print("\nLarge dataset. Using IVFFlat index...")
    try:
        # Calculate appropriate number of lists (sqrt of row count is recommended)
        import math
        lists = max(10, int(math.sqrt(count)))
        
        cur.execute(f"""
            CREATE INDEX face_embeddings_vector_idx 
            ON face_embeddings 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {lists});
        """)
        conn.commit()
        print(f"✓ Created IVFFlat index with {lists} lists")
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        conn.rollback()

# Verify the index
print("\nVerifying indexes...")
cur.execute("""
    SELECT indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename = 'face_embeddings';
""")

indexes = cur.fetchall()
print(f"Current indexes ({len(indexes)}):")
for name, definition in indexes:
    print(f"  • {name}")

# Test a simple query
print("\nTesting query performance...")
cur.execute("""
    SELECT actor_id, actor_name, COUNT(*)
    FROM face_embeddings
    GROUP BY actor_id, actor_name
    LIMIT 5;
""")

print("Sample actors:")
for row in cur.fetchall():
    print(f"  • {row[1]} (ID: {row[0]}): {row[2]} embeddings")

cur.close()
conn.close()

print("\n✓ Index optimization complete!")
print("\nNow try running the pipeline again:")
print("  python3 updated_agentic_pipeline.py input/morgan.jpg --movie 'Bruce Almighty'")
