#!/usr/bin/env python3
"""
Manually test embedding extraction and matching for a specific image.
"""

import cv2
import numpy as np
import psycopg2
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipelines.updated_agentic_pipeline import InsightFaceRecognizer

# Initialize face recognizer
print("Loading InsightFace...")
recognizer = InsightFaceRecognizer()

# Load the cropped image
image_path = "output/morgan_person_1.png"
print(f"\nLoading image: {image_path}")

img = cv2.imread(image_path)
if img is None:
    print(f"❌ Could not load image: {image_path}")
    exit(1)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Extract embedding
print("\nExtracting face embedding...")
embedding = recognizer.extract_embeddings_from_crop(img, debug=True)

if embedding is None:
    print("❌ No face detected in image")
    exit(1)

print(f"✓ Embedding extracted: shape={embedding.shape}, dtype={embedding.dtype}")
print(f"  First 5 values: {embedding[:5]}")
print(f"  Range: [{embedding.min():.3f}, {embedding.max():.3f}]")

# Connect to database
print("\nConnecting to database...")
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=os.getenv('POSTGRES_PORT', '5432'),
    database=os.getenv('POSTGRES_DB', 'face_recognition'),
    user=os.getenv('POSTGRES_USER', 'postgres'),
    password=os.getenv('POSTGRES_PASSWORD', 'postgres')
)

cur = conn.cursor()

# Get all embeddings and calculate similarity manually
print("\nSearching database for matches...")

cur.execute("""
    SELECT actor_id, actor_name, image_path, embedding::text
    FROM face_embeddings;
""")

all_embeddings = cur.fetchall()
print(f"Found {len(all_embeddings)} embeddings in database")

# Calculate similarities
similarities = []
for actor_id, actor_name, img_path, emb_str in all_embeddings:
    # Parse embedding
    emb_str = emb_str.strip('[]')
    db_emb = np.array([float(x) for x in emb_str.split(',')])
    
    # Calculate cosine similarity
    similarity = np.dot(embedding, db_emb) / (np.linalg.norm(embedding) * np.linalg.norm(db_emb))
    
    similarities.append({
        'actor_id': actor_id,
        'actor_name': actor_name,
        'image_path': img_path,
        'similarity': similarity
    })

# Sort by similarity
similarities.sort(key=lambda x: x['similarity'], reverse=True)

# Show top 20 matches
print(f"\n{'='*70}")
print("TOP 20 MATCHES")
print(f"{'='*70}")

for i, match in enumerate(similarities[:20], 1):
    status = "✓" if match['similarity'] >= 0.6 else "✗"
    print(f"{status} {i:2d}. {match['actor_name']:30s} {match['similarity']:.4f} ({int(match['similarity']*100):3d}%)")
    if i <= 5:
        print(f"      Image: {match['image_path']}")

# Check if Jim Carrey is in top matches
print(f"\n{'='*70}")
print("JIM CARREY MATCHES")
print(f"{'='*70}")

jim_matches = [s for s in similarities if 'Jim' in s['actor_name'] or 'Carrey' in s['actor_name']]
if jim_matches:
    for i, match in enumerate(jim_matches, 1):
        rank = similarities.index(match) + 1
        status = "✓" if match['similarity'] >= 0.6 else "✗"
        print(f"{status} Rank {rank:3d}: {match['similarity']:.4f} ({int(match['similarity']*100):3d}%)")
        print(f"   Image: {match['image_path']}")
else:
    print("No Jim Carrey matches found")

# Summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
best = similarities[0]
print(f"Best match: {best['actor_name']}")
print(f"Similarity: {best['similarity']:.4f} ({int(best['similarity']*100)}%)")
print(f"Image: {best['image_path']}")

if best['similarity'] >= 0.6:
    print(f"\n✓ Would be matched with default threshold (0.6)")
else:
    print(f"\n✗ Below default threshold (0.6)")
    print(f"  Use --threshold {best['similarity']:.2f} to match")

cur.close()
conn.close()
