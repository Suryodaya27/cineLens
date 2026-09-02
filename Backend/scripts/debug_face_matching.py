#!/usr/bin/env python3
"""
Debug face matching issues.

This script helps diagnose why faces aren't being matched correctly.
"""

import cv2
import numpy as np
from pathlib import Path
import argparse
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipelines.updated_agentic_pipeline import (
    InsightFaceRecognizer,
    FaceEmbeddingDB,
    TMDBCastFetcher
)


def test_face_detection(image_path: str):
    """Test if face can be detected in an image."""
    print(f"\n{'='*70}")
    print(f"Testing Face Detection: {Path(image_path).name}")
    print(f"{'='*70}\n")
    
    recognizer = InsightFaceRecognizer()
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return None
    
    h, w = img.shape[:2]
    print(f"Image size: {w}x{h}")
    
    # Try to detect faces
    print("\nDetecting faces...")
    embedding = recognizer.extract_embedding(image_path, debug=True)
    
    if embedding is None:
        print("\n❌ No face detected!")
        print("\nPossible issues:")
        print("  • Face is too small or too large")
        print("  • Face is at extreme angle")
        print("  • Image quality is too low")
        print("  • Face is partially occluded")
        return None
    
    print(f"\n✓ Face detected successfully!")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"Embedding range: [{embedding.min():.3f}, {embedding.max():.3f}]")
    
    return embedding


def compare_embeddings(image1: str, image2: str):
    """Compare embeddings between two images."""
    print(f"\n{'='*70}")
    print(f"Comparing Face Embeddings")
    print(f"{'='*70}\n")
    
    recognizer = InsightFaceRecognizer()
    
    print(f"📷 Image 1: {Path(image1).name}")
    print(f"   Path: {image1}")
    emb1 = recognizer.extract_embedding(image1, debug=True)
    
    print(f"\n📷 Image 2: {Path(image2).name}")
    print(f"   Path: {image2}")
    emb2 = recognizer.extract_embedding(image2, debug=True)
    
    if emb1 is None or emb2 is None:
        print("\n❌ Could not extract embeddings from both images")
        return
    
    # Calculate cosine similarity
    similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    print(f"\n{'='*70}")
    print(f"🎯 SIMILARITY SCORE")
    print(f"{'='*70}")
    print(f"Score: {similarity:.4f} ({int(similarity * 100)}%)")
    print(f"{'='*70}")
    
    # Interpretation with visual indicator
    if similarity >= 0.7:
        print("✓✓✓ Very likely the same person")
        print("    Confidence: Very High")
    elif similarity >= 0.6:
        print("✓✓  Likely the same person")
        print("    Confidence: High (default threshold)")
    elif similarity >= 0.5:
        print("⚠️   Possibly the same person (borderline)")
        print("    Confidence: Moderate")
    elif similarity >= 0.4:
        print("⚠️   Unlikely the same person")
        print("    Confidence: Low")
    else:
        print("❌  Different people")
        print("    Confidence: Very Low")
    
    print(f"\n📊 Threshold Guide:")
    print(f"   • Default threshold: 0.6")
    print(f"   • Your similarity: {similarity:.4f}")
    if similarity < 0.6:
        print(f"   • To match this: --threshold {similarity:.2f}")
    
    print(f"\n💡 View images:")
    print(f"   open {image1} {image2}  # macOS")
    print(f"   xdg-open {image1} && xdg-open {image2}  # Linux")


def test_actor_embeddings(actor_name: str, test_image: str):
    """Test matching against a specific actor's cached embeddings."""
    print(f"\n{'='*70}")
    print(f"Testing Match Against: {actor_name}")
    print(f"{'='*70}\n")
    
    recognizer = InsightFaceRecognizer()
    db = FaceEmbeddingDB()
    
    # Extract embedding from test image
    print(f"Test image: {Path(test_image).name}")
    test_embedding = recognizer.extract_embedding(test_image, debug=True)
    
    if test_embedding is None:
        print("\n❌ Could not extract face from test image")
        db.close()
        return
    
    # Search for actor in database
    print(f"\nSearching for '{actor_name}' in database...")
    
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT actor_id, actor_name, COUNT(*) as embedding_count
            FROM face_embeddings
            WHERE LOWER(actor_name) LIKE LOWER(%s)
            GROUP BY actor_id, actor_name;
        """, (f"%{actor_name}%",))
        
        actors = cur.fetchall()
        
        if not actors:
            print(f"\n❌ No embeddings found for '{actor_name}'")
            print("\nRun the pipeline first to cache actor embeddings:")
            print(f"  python3 updated_agentic_pipeline.py image.jpg --movie \"Movie Name\"")
            db.close()
            return
        
        print(f"\nFound {len(actors)} matching actor(s):")
        for actor_id, name, count in actors:
            print(f"  • {name} (ID: {actor_id}, {count} embeddings)")
        
        # Use first match
        actor_id, actor_name_db, _ = actors[0]
        
        # Get all embeddings for this actor
        # Cast embedding to text to get it as a string, then we'll parse it
        cur.execute("""
            SELECT image_path, embedding::text
            FROM face_embeddings
            WHERE actor_id = %s;
        """, (actor_id,))
        
        embeddings = cur.fetchall()
        
        print(f"\nComparing against {len(embeddings)} cached images:")
        print(f"{'='*70}")
        
        similarities = []
        for img_path, emb_str in embeddings:
            # Convert embedding from pgvector text format to numpy array
            # pgvector returns format like: "[0.123,0.456,...]"
            if isinstance(emb_str, str):
                # Remove brackets and split by comma
                emb_str = emb_str.strip('[]')
                emb = np.array([float(x) for x in emb_str.split(',')])
            else:
                emb = np.array(emb_str)
            
            similarity = np.dot(test_embedding, emb) / (
                np.linalg.norm(test_embedding) * np.linalg.norm(emb)
            )
            similarities.append((img_path, Path(img_path).name, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        for img_path, img_name, sim in similarities:
            status = "✓" if sim >= 0.6 else "✗"
            print(f"{status} {img_name}: {sim:.4f} ({int(sim * 100)}%)")
        
        best_match = similarities[0]
        best_path, best_name, best_sim = best_match
        
        print(f"\n{'='*70}")
        print(f"🎯 BEST MATCH")
        print(f"{'='*70}")
        print(f"File: {best_name}")
        print(f"Full path: {best_path}")
        print(f"Similarity: {best_sim:.4f} ({int(best_sim * 100)}%)")
        print(f"{'='*70}")
        
        if best_sim >= 0.6:
            print("✓ Would be matched with default threshold (0.6)")
        else:
            print(f"❌ Below default threshold (0.6)")
            print(f"   Use --threshold {best_sim:.2f} to match")
        
        # Show which image to check
        print(f"\n💡 TIP: View the matched image:")
        print(f"   open {best_path}  # macOS")
        print(f"   xdg-open {best_path}  # Linux")
        
        # Show side-by-side comparison suggestion
        print(f"\n💡 Compare visually:")
        print(f"   python3 debug_face_matching.py --compare {test_image} \"{best_path}\"")
    
    db.close()


def list_cached_actors():
    """List all actors with cached embeddings."""
    print(f"\n{'='*70}")
    print(f"Cached Actors in Database")
    print(f"{'='*70}\n")
    
    db = FaceEmbeddingDB()
    
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT actor_id, actor_name, COUNT(*) as embedding_count
            FROM face_embeddings
            GROUP BY actor_id, actor_name
            ORDER BY actor_name;
        """)
        
        actors = cur.fetchall()
        
        if not actors:
            print("No actors cached yet.")
            print("\nRun the pipeline to cache actors:")
            print("  python3 updated_agentic_pipeline.py image.jpg --movie \"Movie Name\"")
        else:
            for actor_id, name, count in actors:
                print(f"• {name} (ID: {actor_id}, {count} embeddings)")
    
    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Debug face matching issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test if face can be detected in an image
  python3 debug_face_matching.py --test-detection input/image.jpg
  
  # Compare two images to see similarity score
  python3 debug_face_matching.py --compare input/jim1.jpg input/jim2.jpg
  
  # Test matching against cached actor embeddings
  python3 debug_face_matching.py --test-actor "Jim Carrey" input/jim.jpg
  
  # List all cached actors
  python3 debug_face_matching.py --list-actors
        """
    )
    
    parser.add_argument("--test-detection", metavar="IMAGE",
                       help="Test face detection on an image")
    parser.add_argument("--compare", nargs=2, metavar=("IMAGE1", "IMAGE2"),
                       help="Compare embeddings between two images")
    parser.add_argument("--test-actor", nargs=2, metavar=("ACTOR_NAME", "IMAGE"),
                       help="Test matching against cached actor embeddings")
    parser.add_argument("--list-actors", action="store_true",
                       help="List all cached actors")
    
    args = parser.parse_args()
    
    if args.test_detection:
        test_face_detection(args.test_detection)
    elif args.compare:
        compare_embeddings(args.compare[0], args.compare[1])
    elif args.test_actor:
        test_actor_embeddings(args.test_actor[0], args.test_actor[1])
    elif args.list_actors:
        list_cached_actors()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
