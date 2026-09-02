#!/usr/bin/env python3
"""
Test script for the Agentic Pipeline API.

Usage:
    python test_api.py
    python test_api.py --url http://localhost:8000
    python test_api.py --image-url https://example.com/image.jpg --movie "Pathaan"
"""

import requests
import json
import argparse
import time
from typing import Dict


def test_health_check(base_url: str) -> bool:
    """Test the health check endpoint."""
    print("\n" + "="*70)
    print("🏥 Testing Health Check Endpoint")
    print("="*70)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Status: {data['status']}")
        print(f"✓ TMDB Configured: {data['tmdb_configured']}")
        print(f"✓ ImgBB Configured: {data['imgbb_configured']}")
        print(f"✓ Timestamp: {data['timestamp']}")
        
        return True
    
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_analyze_endpoint(base_url: str, image_url: str, movie_name: str,
                         enable_vision: int = 0, similarity_threshold: float = 0.6) -> Dict:
    """Test the analyze endpoint."""
    print("\n" + "="*70)
    print("🎬 Testing Analyze Endpoint")
    print("="*70)
    print(f"Image URL: {image_url}")
    print(f"Movie: {movie_name}")
    print(f"Vision Analysis: {'Enabled' if enable_vision else 'Disabled'}")
    print(f"Similarity Threshold: {similarity_threshold}")
    print("="*70)
    
    payload = {
        "image_url": image_url,
        "movie_name": movie_name,
        "enable_vision": enable_vision,
        "similarity_threshold": similarity_threshold
    }
    
    try:
        print("\n📤 Sending request...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/analyze",
            json=payload,
            timeout=300  # 5 minutes timeout for vision analysis
        )
        
        elapsed_time = time.time() - start_time
        
        response.raise_for_status()
        result = response.json()
        
        print(f"\n✓ Request completed in {elapsed_time:.2f}s")
        print(f"✓ Server processing time: {result.get('processing_time', 0):.2f}s")
        
        if result.get('success'):
            print("\n" + "="*70)
            print("📊 RESULTS")
            print("="*70)
            
            data = result.get('data', {})
            
            # Movie context
            movie_ctx = data.get('movie_context', {})
            print(f"\n🎬 Movie: {movie_ctx.get('title')} ({movie_ctx.get('year')})")
            print(f"   Cast: {len(movie_ctx.get('cast', []))} members")
            
            # Detections summary
            summary = data.get('detections_summary', {})
            print(f"\n🔍 Detections:")
            print(f"   • People: {summary.get('people', 0)}")
            print(f"   • Products: {summary.get('products', 0)}")
            print(f"   • Animals: {summary.get('animals', 0)}")
            print(f"   • Vehicles: {summary.get('vehicles', 0)}")
            print(f"   • Electronics: {summary.get('electronics', 0)}")
            print(f"   • Furniture: {summary.get('furniture', 0)}")
            print(f"   • Other: {summary.get('other_objects', 0)}")
            
            # People
            people = data.get('people', [])
            if people:
                print(f"\n👤 Identified People:")
                for idx, person in enumerate(people, 1):
                    if person.get('name'):
                        char = f" as {person['character']}" if person.get('character') else ""
                        print(f"   {idx}. {person['name']}{char}")
                        print(f"      Confidence: {person.get('confidence', 0)}%")
                        print(f"      Crop Image: {person.get('crop_image', 'N/A')}")
                        print(f"      Hosted: {'✓' if person.get('crop_image_hosted') else '✗'}")
                        
                        if enable_vision:
                            clothing = person.get('clothing', {})
                            print(f"      Clothing: {clothing.get('description', 'N/A')}")
                            print(f"      Colors: {', '.join(clothing.get('colors', []))}")
                    else:
                        print(f"   {idx}. Unknown person")
                        print(f"      Crop Image: {person.get('crop_image', 'N/A')}")
            
            # Scene analysis
            if enable_vision:
                scene = data.get('scene_analysis', {})
                if scene:
                    print(f"\n🎬 Scene Analysis:")
                    print(f"   Setting: {scene.get('setting', 'N/A')}")
                    print(f"   Lighting: {scene.get('lighting', 'N/A')}")
                    print(f"   Mood: {scene.get('mood', 'N/A')}")
                    print(f"   Time of Day: {scene.get('time_of_day', 'N/A')}")
            
            # Products
            products = data.get('products', [])
            if products:
                print(f"\n📦 Products:")
                for idx, product in enumerate(products, 1):
                    print(f"   {idx}. {product.get('product_type', 'Unknown')}")
                    if product.get('brand'):
                        print(f"      Brand: {product['brand']}")
                    print(f"      Crop Image: {product.get('crop_image', 'N/A')}")
            
            print("\n" + "="*70)
            
            return result
        else:
            print(f"\n❌ Analysis failed: {result.get('message')}")
            return result
    
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timed out after {elapsed_time:.2f}s")
        print("   Try with enable_vision=0 for faster processing")
        return None
    
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        try:
            error_data = e.response.json()
            print(f"   Detail: {error_data.get('detail', 'No details')}")
        except:
            print(f"   Response: {e.response.text}")
        return None
    
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_result(result: Dict, filename: str = "api_test_result.json"):
    """Save result to JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Result saved to: {filename}")
    except Exception as e:
        print(f"\n⚠️  Failed to save result: {e}")


def test_actor_movies(base_url: str, actor_name: str, limit: int = 10, sort_by: str = "recent") -> Dict:
    """Test the actor movies endpoint."""
    print("\n" + "="*70)
    print("🎬 Testing Actor Movies Endpoint")
    print("="*70)
    print(f"Actor: {actor_name}")
    print(f"Limit: {limit}")
    print(f"Sort by: {sort_by}")
    print("="*70)
    
    payload = {
        "actor_name": actor_name,
        "limit": limit,
        "sort_by": sort_by
    }
    
    try:
        print("\n📤 Sending request...")
        response = requests.post(
            f"{base_url}/api/more-movies",
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            print("\n" + "="*70)
            print("📊 RESULTS")
            print("="*70)
            
            data = result.get('data', {})
            
            # Actor info
            print(f"\n🎭 Actor: {data.get('name')}")
            print(f"   Known for: {data.get('known_for_department', 'N/A')}")
            print(f"   Total credits: {data.get('total_credits', 0)}")
            if data.get('birthday'):
                print(f"   Birthday: {data['birthday']}")
            if data.get('place_of_birth'):
                print(f"   Birthplace: {data['place_of_birth']}")
            if data.get('profile_image'):
                print(f"   Profile: {data['profile_image']}")
            
            # Movies
            movies = data.get('movies', [])
            print(f"\n🎬 Movies ({len(movies)}):")
            for idx, movie in enumerate(movies, 1):
                title = movie.get('title', 'Unknown')
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'TBA'
                rating = movie.get('vote_average', 0)
                character = movie.get('character', 'N/A')
                poster = movie.get('poster_path')
                
                print(f"\n   {idx}. {title} ({year})")
                print(f"      Rating: ⭐ {rating}/10")
                print(f"      Character: {character}")
                if poster:
                    print(f"      Poster: {poster}")
            
            print("\n" + "="*70)
            
            return result
        else:
            print(f"\n❌ Request failed: {result.get('message')}")
            return result
    
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        try:
            error_data = e.response.json()
            print(f"   Detail: {error_data.get('detail', 'No details')}")
        except:
            print(f"   Response: {e.response.text}")
        return None
    
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Test the Agentic Pipeline API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default settings
  python test_api.py
  
  # Test with custom image and movie
  python test_api.py --image-url "https://example.com/image.jpg" --movie "Pathaan"
  
  # Test with vision analysis enabled
  python test_api.py --enable-vision --movie "Leo"
  
  # Test actor movies endpoint
  python test_api.py --test-actor-movies --actor "Shah Rukh Khan"
  
  # Test with custom API URL
  python test_api.py --url http://192.168.1.100:8000
        """
    )
    
    parser.add_argument("--url", default="http://localhost:8000",
                       help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--image-url",
                       default="https://i.ibb.co/9ZQZ8Zq/srk-test.jpg",
                       help="Image URL to analyze")
    parser.add_argument("--movie", default="Pathaan",
                       help="Movie or series name")
    parser.add_argument("--enable-vision", action="store_true",
                       help="Enable vision analysis (slower but detailed)")
    parser.add_argument("--threshold", type=float, default=0.6,
                       help="Similarity threshold (0.0-1.0, default: 0.6)")
    parser.add_argument("--save", action="store_true",
                       help="Save result to JSON file")
    parser.add_argument("--skip-health", action="store_true",
                       help="Skip health check")
    parser.add_argument("--test-actor-movies", action="store_true",
                       help="Test actor movies endpoint instead of analyze")
    parser.add_argument("--actor", default="Shah Rukh Khan",
                       help="Actor name for movies endpoint (default: Shah Rukh Khan)")
    parser.add_argument("--sort-by", choices=["recent", "rating"], default="recent",
                       help="Sort movies by recent or rating (default: recent)")
    parser.add_argument("--limit", type=int, default=10,
                       help="Number of movies to fetch (default: 10)")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧪 AGENTIC PIPELINE API TEST")
    print("="*70)
    print(f"API URL: {args.url}")
    print("="*70)
    
    # Test health check
    if not args.skip_health:
        if not test_health_check(args.url):
            print("\n⚠️  Health check failed. Is the server running?")
            print(f"   Start server with: python api.py")
            return
    
    # Test actor movies endpoint or analyze endpoint
    if args.test_actor_movies:
        result = test_actor_movies(
            args.url,
            args.actor,
            limit=args.limit,
            sort_by=args.sort_by
        )
    else:
        result = test_analyze_endpoint(
            args.url,
            args.image_url,
            args.movie,
            enable_vision=1 if args.enable_vision else 0,
            similarity_threshold=args.threshold
        )
    
    # Save result if requested
    if result and args.save:
        save_result(result)
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
