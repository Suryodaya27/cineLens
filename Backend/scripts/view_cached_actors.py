#!/usr/bin/env python3
"""
View cached actor images and database embeddings.

This script shows you:
1. Which actors have cached images
2. Where the images are stored
3. How many embeddings are in the database
"""

import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def view_cached_images():
    """Show all cached actor images."""
    cache_dir = Path("cache/tmdb/actors")
    
    if not cache_dir.exists():
        print("❌ No cache directory found")
        print(f"   Expected: {cache_dir.absolute()}")
        return
    
    actor_dirs = sorted([d for d in cache_dir.iterdir() if d.is_dir()])
    
    if not actor_dirs:
        print("📁 Cache directory exists but no actors cached yet")
        print(f"   Location: {cache_dir.absolute()}")
        return
    
    print(f"📁 Actor Images Cache: {cache_dir.absolute()}")
    print(f"{'='*70}\n")
    
    total_images = 0
    for actor_dir in actor_dirs:
        # Extract actor name from directory name (format: actor_<id>_<name>)
        dir_name = actor_dir.name
        if dir_name.startswith("actor_"):
            parts = dir_name.split("_", 2)
            if len(parts) >= 3:
                actor_id = parts[1]
                actor_name = parts[2].replace("_", " ")
            else:
                actor_id = parts[1] if len(parts) > 1 else "unknown"
                actor_name = "Unknown"
        else:
            actor_id = "unknown"
            actor_name = dir_name
        
        images = list(actor_dir.glob("*.jpg"))
        total_images += len(images)
        
        print(f"👤 {actor_name} (ID: {actor_id})")
        print(f"   📂 {actor_dir}")
        print(f"   🖼️  {len(images)} images:")
        for img in sorted(images):
            size_kb = img.stat().st_size / 1024
            print(f"      • {img.name} ({size_kb:.1f} KB)")
        print()
    
    print(f"{'='*70}")
    print(f"Total: {len(actor_dirs)} actors, {total_images} images")
    print(f"{'='*70}\n")


def view_database_embeddings():
    """Show embeddings stored in database."""
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'face_recognition'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        print(f"🗄️  Database: {db_config['database']} @ {db_config['host']}")
        print(f"{'='*70}\n")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get summary by actor
            cur.execute("""
                SELECT 
                    actor_id,
                    actor_name,
                    COUNT(*) as embedding_count,
                    MIN(created_at) as first_cached,
                    MAX(created_at) as last_cached
                FROM face_embeddings
                GROUP BY actor_id, actor_name
                ORDER BY actor_name;
            """)
            
            actors = cur.fetchall()
            
            if not actors:
                print("📊 No embeddings in database yet")
                print("   Run the pipeline to generate embeddings")
                return
            
            print(f"📊 Face Embeddings Summary:")
            print(f"{'='*70}\n")
            
            total_embeddings = 0
            for actor in actors:
                total_embeddings += actor['embedding_count']
                print(f"👤 {actor['actor_name']} (ID: {actor['actor_id']})")
                print(f"   Embeddings: {actor['embedding_count']}")
                print(f"   First cached: {actor['first_cached']}")
                print(f"   Last cached: {actor['last_cached']}")
                
                # Get image paths for this actor
                cur.execute("""
                    SELECT image_path
                    FROM face_embeddings
                    WHERE actor_id = %s
                    ORDER BY created_at;
                """, (actor['actor_id'],))
                
                images = cur.fetchall()
                print(f"   Images with embeddings:")
                for img in images:
                    img_path = Path(img['image_path'])
                    print(f"      • {img_path.name}")
                print()
            
            print(f"{'='*70}")
            print(f"Total: {len(actors)} actors, {total_embeddings} embeddings")
            print(f"{'='*70}\n")
        
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print(f"\n   Make sure PostgreSQL is running:")
        print(f"   • macOS: brew services start postgresql@15")
        print(f"   • Linux: sudo systemctl start postgresql")
        print(f"   • Docker: docker-compose up -d")
    except Exception as e:
        print(f"❌ Error: {e}")


def clear_cache(confirm=False):
    """Clear cached images and database embeddings."""
    if not confirm:
        print("⚠️  This will delete all cached actor images and database embeddings!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
    
    # Clear image cache
    cache_dir = Path("cache/tmdb/actors")
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Cleared image cache")
    
    # Clear database
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'face_recognition'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("TRUNCATE face_embeddings;")
            conn.commit()
        conn.close()
        print("✓ Cleared database embeddings")
    except Exception as e:
        print(f"⚠️  Could not clear database: {e}")
    
    print("\n✓ Cache cleared!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="View cached actor images and database embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View all cached data
  python3 view_cached_actors.py
  
  # View only images
  python3 view_cached_actors.py --images-only
  
  # View only database
  python3 view_cached_actors.py --db-only
  
  # Clear all cache
  python3 view_cached_actors.py --clear
        """
    )
    parser.add_argument("--images-only", action="store_true",
                       help="Show only cached images")
    parser.add_argument("--db-only", action="store_true",
                       help="Show only database embeddings")
    parser.add_argument("--clear", action="store_true",
                       help="Clear all cached data")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_cache()
        return
    
    print("\n" + "="*70)
    print("CACHED ACTOR DATA VIEWER")
    print("="*70 + "\n")
    
    if args.db_only:
        view_database_embeddings()
    elif args.images_only:
        view_cached_images()
    else:
        view_cached_images()
        view_database_embeddings()


if __name__ == "__main__":
    main()
