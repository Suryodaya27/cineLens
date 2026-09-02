#!/usr/bin/env python3
"""
Check for mismatches between TMDB cast and cached embeddings.

This helps diagnose why some actors aren't being matched.
"""

import os
import psycopg2
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipelines.updated_agentic_pipeline import TMDBCastFetcher, FaceEmbeddingDB


def check_movie_cast(movie_title: str):
    """Check which cast members are cached vs not cached."""
    print(f"\n{'='*70}")
    print(f"Checking Cast for: {movie_title}")
    print(f"{'='*70}\n")
    
    # Fetch cast from TMDB
    tmdb = TMDBCastFetcher()
    title_data = tmdb.search_title(movie_title)
    
    if not title_data:
        print(f"❌ Movie not found: {movie_title}")
        return
    
    tmdb_id = title_data['id']
    media_type = title_data['media_type']
    
    print(f"Found: {title_data.get('title') or title_data.get('name')}")
    print(f"Type: {media_type}")
    print(f"TMDB ID: {tmdb_id}\n")
    
    cast_list = tmdb.get_cast(tmdb_id, media_type, max_cast=20)
    
    if not cast_list:
        print("❌ No cast found")
        return
    
    print(f"Cast List ({len(cast_list)} members):")
    print(f"{'='*70}\n")
    
    # Check database
    db = FaceEmbeddingDB()
    
    cached_actors = []
    missing_actors = []
    
    for idx, member in enumerate(cast_list, 1):
        actor_id = member['id']
        actor_name = member['name']
        character = member.get('character', 'N/A')
        
        # Check if actor has embeddings
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM face_embeddings 
                WHERE actor_id = %s;
            """, (actor_id,))
            
            count = cur.fetchone()[0]
        
        if count > 0:
            print(f"✓ [{idx:2d}] {actor_name}")
            print(f"      Character: {character}")
            print(f"      Embeddings: {count}")
            cached_actors.append((actor_id, actor_name, count))
        else:
            print(f"✗ [{idx:2d}] {actor_name}")
            print(f"      Character: {character}")
            print(f"      Embeddings: 0 (NOT CACHED)")
            missing_actors.append((actor_id, actor_name))
        print()
    
    db.close()
    
    # Summary
    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total cast: {len(cast_list)}")
    print(f"Cached: {len(cached_actors)} actors")
    print(f"Missing: {len(missing_actors)} actors")
    
    if missing_actors:
        print(f"\n⚠️  Missing actors won't be matched!")
        print(f"\nTo cache missing actors, run:")
        print(f'  python3 updated_agentic_pipeline.py input/image.jpg --movie "{movie_title}"')
    else:
        print(f"\n✓ All cast members are cached!")


def check_actor_in_database(actor_name: str):
    """Check if an actor is in the database."""
    print(f"\n{'='*70}")
    print(f"Checking Database for: {actor_name}")
    print(f"{'='*70}\n")
    
    db = FaceEmbeddingDB()
    
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT actor_id, actor_name, COUNT(*) as embedding_count
            FROM face_embeddings
            WHERE LOWER(actor_name) LIKE LOWER(%s)
            GROUP BY actor_id, actor_name;
        """, (f"%{actor_name}%",))
        
        actors = cur.fetchall()
    
    if not actors:
        print(f"❌ No embeddings found for '{actor_name}'")
        print(f"\nPossible reasons:")
        print(f"  1. Actor not in any cached movie cast")
        print(f"  2. Actor's profile images had no detectable faces")
        print(f"  3. Actor name spelling is different")
    else:
        print(f"Found {len(actors)} matching actor(s):\n")
        for actor_id, name, count in actors:
            print(f"✓ {name}")
            print(f"  Actor ID: {actor_id}")
            print(f"  Embeddings: {count}")
            
            # Show which images
            with db.conn.cursor() as cur:
                cur.execute("""
                    SELECT image_path
                    FROM face_embeddings
                    WHERE actor_id = %s;
                """, (actor_id,))
                
                images = cur.fetchall()
                print(f"  Images:")
                for img_path, in images:
                    print(f"    • {Path(img_path).name}")
            print()
    
    db.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check for cast/database mismatches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check which cast members are cached for a movie
  python3 check_cast_mismatch.py --movie "Bruce Almighty"
  
  # Check if a specific actor is in the database
  python3 check_cast_mismatch.py --actor "Jim Carrey"
        """
    )
    
    parser.add_argument("--movie", help="Check cast for a movie")
    parser.add_argument("--actor", help="Check if actor is in database")
    
    args = parser.parse_args()
    
    if args.movie:
        check_movie_cast(args.movie)
    elif args.actor:
        check_actor_in_database(args.actor)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
