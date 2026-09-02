#!/usr/bin/env python3
"""
Fix duplicate embeddings in database.
Remove old embeddings with path 'cache/tmdb/actor_XXX/' and keep only 'cache/tmdb/actors/actor_XXX_Name/'
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

# Find duplicates
print("Checking for duplicate embeddings...")
cur.execute("""
    SELECT image_path, COUNT(*) 
    FROM face_embeddings 
    GROUP BY image_path 
    HAVING COUNT(*) > 1;
""")

duplicates = cur.fetchall()
print(f"Found {len(duplicates)} duplicate image paths")

# Count old vs new paths
cur.execute("""
    SELECT COUNT(*) 
    FROM face_embeddings 
    WHERE image_path LIKE 'cache/tmdb/actor_%' 
    AND image_path NOT LIKE 'cache/tmdb/actors/%';
""")
old_count = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) 
    FROM face_embeddings 
    WHERE image_path LIKE 'cache/tmdb/actors/%';
""")
new_count = cur.fetchone()[0]

print(f"\nOld path format: {old_count} embeddings")
print(f"New path format: {new_count} embeddings")

# Delete old format embeddings
print("\nDeleting old format embeddings...")
cur.execute("""
    DELETE FROM face_embeddings 
    WHERE image_path LIKE 'cache/tmdb/actor_%' 
    AND image_path NOT LIKE 'cache/tmdb/actors/%';
""")

deleted = cur.rowcount
conn.commit()

print(f"✓ Deleted {deleted} old embeddings")

# Verify
cur.execute("SELECT COUNT(*) FROM face_embeddings;")
total = cur.fetchone()[0]
print(f"\nRemaining embeddings: {total}")

cur.close()
conn.close()

print("\n✓ Database cleaned!")
print("\nNow run the pipeline again:")
print("  python3 updated_agentic_pipeline.py input/morgan.jpg --movie 'Bruce Almighty'")
