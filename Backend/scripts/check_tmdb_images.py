#!/usr/bin/env python3
"""
Check how many images TMDB has for actors in a movie.
"""

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipelines.updated_agentic_pipeline import TMDBCastFetcher

def check_movie_images(movie_title: str, max_cast: int = 10):
    """Check image availability for a movie's cast."""
    print(f"\n{'='*70}")
    print(f"Checking Image Availability: {movie_title}")
    print(f"{'='*70}\n")
    
    tmdb = TMDBCastFetcher()
    
    # Search for movie
    title_data = tmdb.search_title(movie_title)
    if not title_data:
        print(f"❌ Movie not found: {movie_title}")
        return
    
    tmdb_id = title_data['id']
    media_type = title_data['media_type']
    
    print(f"Found: {title_data.get('title') or title_data.get('name')}")
    print(f"Type: {media_type}\n")
    
    # Get cast
    cast_list = tmdb.get_cast(tmdb_id, media_type, max_cast)
    
    print(f"{'='*70}")
    print(f"IMAGE AVAILABILITY FOR TOP {len(cast_list)} CAST MEMBERS")
    print(f"{'='*70}\n")
    
    total_images = 0
    for idx, member in enumerate(cast_list, 1):
        actor_id = member['id']
        actor_name = member['name']
        character = member.get('character', 'N/A')
        
        # Get image count
        url = f"{tmdb.base_url}/person/{actor_id}/images"
        params = {'api_key': tmdb.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            image_count = len(data.get('profiles', []))
            total_images += image_count
            
            # Visual indicator
            if image_count >= 20:
                indicator = "🟢 Excellent"
            elif image_count >= 10:
                indicator = "🟡 Good"
            elif image_count >= 5:
                indicator = "🟠 Moderate"
            else:
                indicator = "🔴 Limited"
            
            print(f"{idx:2d}. {actor_name:30s} {indicator}")
            print(f"    Character: {character}")
            print(f"    Images: {image_count}")
            print()
            
        except Exception as e:
            print(f"{idx:2d}. {actor_name:30s} ❌ Error")
            print(f"    {e}\n")
    
    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total cast members: {len(cast_list)}")
    print(f"Total images available: {total_images}")
    print(f"Average per actor: {total_images / len(cast_list):.1f}")
    
    print(f"\n💡 RECOMMENDATION:")
    avg = total_images / len(cast_list)
    if avg >= 20:
        recommended = 15
    elif avg >= 10:
        recommended = 10
    else:
        recommended = 5
    
    print(f"   Use --images-per-actor {recommended} for this movie")
    print(f"\n   python3 updated_agentic_pipeline.py input/image.jpg \\")
    print(f"     --movie \"{movie_title}\" \\")
    print(f"     --images-per-actor {recommended}")


def check_actor_images(actor_name: str):
    """Check image availability for a specific actor."""
    print(f"\n{'='*70}")
    print(f"Checking Images for: {actor_name}")
    print(f"{'='*70}\n")
    
    tmdb = TMDBCastFetcher()
    
    # Search for actor
    url = f"{tmdb.base_url}/search/person"
    params = {
        'api_key': tmdb.api_key,
        'query': actor_name,
        'language': 'en-US'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data['results']:
            print(f"❌ Actor not found: {actor_name}")
            return
        
        actor = data['results'][0]
        actor_id = actor['id']
        actor_name = actor['name']
        
        print(f"Found: {actor_name} (ID: {actor_id})")
        print(f"Known for: {actor.get('known_for_department', 'N/A')}\n")
        
        # Get images
        url = f"{tmdb.base_url}/person/{actor_id}/images"
        params = {'api_key': tmdb.api_key}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        profiles = data.get('profiles', [])
        
        print(f"{'='*70}")
        print(f"IMAGE DETAILS")
        print(f"{'='*70}")
        print(f"Total images: {len(profiles)}\n")
        
        if profiles:
            print("Sample images (first 10):")
            for idx, profile in enumerate(profiles[:10], 1):
                width = profile.get('width', 0)
                height = profile.get('height', 0)
                aspect = profile.get('aspect_ratio', 0)
                print(f"  {idx:2d}. {width}x{height} (aspect: {aspect:.2f})")
            
            if len(profiles) > 10:
                print(f"  ... and {len(profiles) - 10} more")
        
        print(f"\n💡 RECOMMENDATION:")
        if len(profiles) >= 20:
            print(f"   Excellent! Use --images-per-actor 15-20")
        elif len(profiles) >= 10:
            print(f"   Good! Use --images-per-actor 10")
        elif len(profiles) >= 5:
            print(f"   Moderate. Use --images-per-actor 5")
        else:
            print(f"   Limited images. Use all {len(profiles)} available")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check TMDB image availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check images for a movie's cast
  python3 check_tmdb_images.py --movie "Bruce Almighty"
  
  # Check images for a specific actor
  python3 check_tmdb_images.py --actor "Jim Carrey"
  
  # Check more cast members
  python3 check_tmdb_images.py --movie "Avengers" --max-cast 20
        """
    )
    
    parser.add_argument("--movie", help="Check images for movie cast")
    parser.add_argument("--actor", help="Check images for specific actor")
    parser.add_argument("--max-cast", type=int, default=10,
                       help="Max cast members to check (default: 10)")
    
    args = parser.parse_args()
    
    if args.movie:
        check_movie_images(args.movie, args.max_cast)
    elif args.actor:
        check_actor_images(args.actor)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
