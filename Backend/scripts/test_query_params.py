#!/usr/bin/env python3
"""
Test the exact query used in the pipeline to see why it returns 0 rows.
"""

import psycopg2
import os
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipelines.updated_agentic_pipeline import InsightFaceRecognizer
import cv2

# Load the image and extract embedding
print("Loading image and extracting embedding...")
recognizer = InsightFaceRecognizer()
img = cv2.imread("output/morgan_person_1.png")
embedding = recognizer.extract_embeddings_from_crop(img, debug=False)
embedding_list = embedding.tolist()

print(f"Embedding: shape={embedding.shape}, type={type(embedding_list)}")
print(f"First 3 values: {embedding_list[:3]}")

# Connect to database
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=os.getenv('POSTGRES_PORT', '5432'),
    database=os.getenv('POSTGRES_DB', 'face_recognition'),
    user=os.getenv('POSTGRES_USER', 'postgres'),
    password=os.getenv('POSTGRES_PASSWORD', 'postgres')
)

cur = conn.cursor()

# Test 1: Query without actor filter (like manual test)
print("\n" + "="*70)
print("TEST 1: Query WITHOUT actor filter")
print("="*70)

query1 = """
    SELECT actor_id, actor_name, image_path,
           1 - (embedding <=> %s::vector) as similarity
    FROM face_embeddings
    ORDER BY embedding <=> %s::vector LIMIT 5
"""
params1 = [embedding_list, embedding_list]

try:
    cur.execute(query1, params1)
    rows1 = cur.fetchall()
    print(f"✓ Query returned {len(rows1)} rows")
    for row in rows1[:3]:
        print(f"  {row[1]}: {row[3]:.4f}")
except Exception as e:
    print(f"❌ Query failed: {e}")

# Test 2: Query WITH actor filter (like pipeline)
print("\n" + "="*70)
print("TEST 2: Query WITH actor filter (actor_ids=[206, 192, ...])")
print("="*70)

actor_ids = [206, 192, 4491, 4492, 4493]
query2 = """
    SELECT actor_id, actor_name, image_path,
           1 - (embedding <=> %s::vector) as similarity
    FROM face_embeddings
    WHERE actor_id = ANY(%s)
    ORDER BY embedding <=> %s::vector LIMIT 5
"""
params2 = [embedding_list, actor_ids, embedding_list]

print(f"Actor IDs: {actor_ids}")
print(f"Params: [embedding_list, actor_ids, embedding_list]")

try:
    cur.execute(query2, params2)
    rows2 = cur.fetchall()
    print(f"✓ Query returned {len(rows2)} rows")
    for row in rows2[:3]:
        print(f"  {row[1]}: {row[3]:.4f}")
except Exception as e:
    print(f"❌ Query failed: {e}")

# Test 3: Check if actor 206 has embeddings
print("\n" + "="*70)
print("TEST 3: Check actor 206 embeddings")
print("="*70)

cur.execute("""
    SELECT COUNT(*), MIN(image_path), MAX(image_path)
    FROM face_embeddings
    WHERE actor_id = 206;
""")
count, min_path, max_path = cur.fetchone()
print(f"Actor 206 (Jim Carrey) has {count} embeddings")
print(f"  Min path: {min_path}")
print(f"  Max path: {max_path}")

# Test 4: Try the query with just actor 206
print("\n" + "="*70)
print("TEST 4: Query with ONLY actor 206")
print("="*70)

query4 = """
    SELECT actor_id, actor_name, image_path,
           1 - (embedding <=> %s::vector) as similarity
    FROM face_embeddings
    WHERE actor_id = 206
    ORDER BY embedding <=> %s::vector LIMIT 5
"""
params4 = [embedding_list, embedding_list]

try:
    cur.execute(query4, params4)
    rows4 = cur.fetchall()
    print(f"✓ Query returned {len(rows4)} rows")
    for row in rows4:
        print(f"  {row[1]}: {row[3]:.4f} - {row[2]}")
except Exception as e:
    print(f"❌ Query failed: {e}")

cur.close()
conn.close()

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("If TEST 1 works but TEST 2 doesn't, there's an issue with the actor_ids filter")
print("If TEST 4 works, then actor 206 embeddings are fine")
