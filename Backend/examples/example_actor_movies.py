#!/usr/bin/env python3
"""
Example: Get actor movies from TMDB API.

Usage:
    python example_actor_movies.py
    python example_actor_movies.py --actor "Tom Cruise" --sort rating
"""

import requests
import argparse


def get_actor_movies(actor_name: str, limit: int = 10, sort_by: str = "recent"):
    """Get actor's movies from the API."""
    
    url = "http://localhost:8000/api/more-movies"
    
    payload = {
        "actor_name": actor_name,
        "limit": limit,
        "sort_by": sort_by
    }
    
    try:
        print(f"🔍 Fetching movies for: {actor_name}")
        print(f"   Sort by: {sort_by}")
        print(f"   Limit: {limit}\n")
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result["success"]:
            actor = result["data"]
            
            print(f"{'='*70}")
            print(f"🎭 {actor['name']}")
            print(f"{'='*70}")
            print(f"Known for: {actor.get('known_for_department', 'N/A')}")
            print(f"Total credits: {actor['total_credits']}")
            
            if actor.get('birthday'):
                print(f"Birthday: {actor['birthday']}")
            
            if actor.get('place_of_birth'):
                print(f"Birthplace: {actor['place_of_birth']}")
            
            if actor.get('profile_image'):
                print(f"Profile: {actor['profile_image']}")
            
            print(f"\n{'='*70}")
            print(f"🎬 Movies ({len(actor['movies'])})")
            print(f"{'='*70}\n")
            
            for idx, movie in enumerate(actor["movies"], 1):
                title = movie.get('title', 'Unknown')
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'TBA'
                rating = movie.get('vote_average', 0)
                character = movie.get('character', 'N/A')
                poster = movie.get('poster_path')
                
                print(f"{idx}. {title} ({year})")
                print(f"   Rating: ⭐ {rating}/10")
                print(f"   Character: {character}")
                
                if poster:
                    print(f"   Poster: {poster}")
                
                print()
            
            return actor
        
        else:
            print(f"❌ Error: {result['message']}")
            return None
    
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API")
        print("   Make sure the server is running: python api.py")
        return None
    
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        try:
            error_data = e.response.json()
            print(f"   Detail: {error_data.get('detail', 'No details')}")
        except:
            pass
        return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Get actor movies from TMDB API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get recent movies for Shah Rukh Khan
  python example_actor_movies.py
  
  # Get top rated movies for Tom Cruise
  python example_actor_movies.py --actor "Tom Cruise" --sort rating
  
  # Get 20 recent movies for Leonardo DiCaprio
  python example_actor_movies.py --actor "Leonardo DiCaprio" --limit 20
        """
    )
    
    parser.add_argument("--actor", default="Shah Rukh Khan",
                       help="Actor name (default: Shah Rukh Khan)")
    parser.add_argument("--limit", type=int, default=10,
                       help="Number of movies to fetch (default: 10)")
    parser.add_argument("--sort", choices=["recent", "rating"], default="recent",
                       help="Sort by recent or rating (default: recent)")
    
    args = parser.parse_args()
    
    get_actor_movies(args.actor, args.limit, args.sort)


if __name__ == "__main__":
    main()
