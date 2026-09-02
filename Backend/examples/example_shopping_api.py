#!/usr/bin/env python3
"""
Example: Get shopping recommendations from analysis data.

This demonstrates the complete workflow:
1. Analyze image with /analyze endpoint
2. Get shopping recommendations with /api/shopping-recommendations endpoint

Usage:
    python example_shopping_api.py
    python example_shopping_api.py --image-url "https://example.com/image.jpg" --movie "Pathaan"
"""

import requests
import json
import argparse


def analyze_image(image_url: str, movie_name: str, enable_vision: int = 1):
    """Step 1: Analyze image to get clothing and product data."""
    
    print(f"{'='*70}")
    print(f"STEP 1: Analyzing Image")
    print(f"{'='*70}")
    print(f"Image: {image_url}")
    print(f"Movie: {movie_name}")
    print(f"Vision Analysis: {'Enabled' if enable_vision else 'Disabled'}\n")
    
    url = "http://localhost:8000/analyze"
    
    payload = {
        "image_url": image_url,
        "movie_name": movie_name,
        "enable_vision": enable_vision,
        "similarity_threshold": 0.6
    }
    
    try:
        print("📤 Sending analysis request...")
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        
        if result["success"]:
            data = result["data"]
            print(f"✓ Analysis complete in {result['processing_time']:.2f}s")
            print(f"  People detected: {len(data.get('people', []))}")
            print(f"  Products detected: {len(data.get('products', []))}")
            print(f"  Electronics detected: {len(data.get('electronics', []))}")
            print(f"  Furniture detected: {len(data.get('furniture', []))}")
            print()
            
            return data
        else:
            print(f"❌ Analysis failed: {result['message']}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_shopping_recommendations(analysis_data: dict, amazon_region: str = "com"):
    """Step 2: Get shopping recommendations from analysis data."""
    
    print(f"{'='*70}")
    print(f"STEP 2: Getting Shopping Recommendations")
    print(f"{'='*70}")
    print(f"Amazon Region: {amazon_region}\n")
    
    url = "http://localhost:8000/api/shopping-recommendations"
    
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 5,
        "max_visual_results": 10,
        "amazon_region": amazon_region
    }
    
    try:
        print("📤 Sending shopping request...")
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        
        if result["success"]:
            data = result["data"]
            summary = data.get('summary', {})
            
            print(f"✓ Shopping recommendations complete")
            print(f"  Total searches: {summary.get('total_searches', 0)}")
            print(f"  Text searches: {summary.get('text_searches', 0)}")
            print(f"  Visual searches: {summary.get('visual_searches', 0)}")
            print(f"  Products found: {summary.get('total_products_found', 0)}")
            print()
            
            return data
        else:
            print(f"❌ Shopping failed: {result['message']}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def display_shopping_results(shopping_data: dict):
    """Display shopping results in a readable format."""
    
    print(f"{'='*70}")
    print(f"SHOPPING RESULTS")
    print(f"{'='*70}\n")
    
    results = shopping_data.get('shopping_results', [])
    
    if not results:
        print("No shopping results found")
        return
    
    # Group by search method
    text_results = [r for r in results if r.get('search_method') == 'text']
    visual_results = [r for r in results if r.get('search_method') == 'visual']
    
    if text_results:
        print(f"🔤 TEXT SEARCH (Amazon) - {len(text_results)} items\n")
        for item in text_results:
            print(f"📦 {item['category'].upper()}: {item['type']}")
            print(f"   Query: {item.get('search_query', 'N/A')}")
            print(f"   Products: {len(item['products'])}\n")
            
            for i, product in enumerate(item['products'][:3], 1):
                print(f"   {i}. {product['title'][:60]}...")
                if product.get('price'):
                    print(f"      Price: {product['price']}")
                if product.get('rating'):
                    print(f"      Rating: {product['rating']}")
                if product.get('link'):
                    print(f"      Link: {product['link']}")
                print()
            
            if len(item['products']) > 3:
                print(f"   ... and {len(item['products']) - 3} more\n")
    
    if visual_results:
        print(f"\n👁️  VISUAL SEARCH (Google Lens) - {len(visual_results)} items\n")
        for item in visual_results:
            print(f"📦 {item['category'].upper()}: {item['type']}")
            print(f"   Products: {len(item['products'])}\n")
            
            for i, product in enumerate(item['products'][:3], 1):
                print(f"   {i}. {product['title'][:60]}...")
                if product.get('price'):
                    print(f"      Price: {product['price']}")
                if product.get('source'):
                    print(f"      Source: {product['source']}")
                if product.get('link'):
                    print(f"      Link: {product['link']}")
                print()
            
            if len(item['products']) > 3:
                print(f"   ... and {len(item['products']) - 3} more\n")


def main():
    parser = argparse.ArgumentParser(
        description="Complete workflow: Analyze image and get shopping recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze and get shopping recommendations
  python example_shopping_api.py
  
  # Custom image and movie
  python example_shopping_api.py --image-url "https://example.com/image.jpg" --movie "Pathaan"
  
  # Use Amazon India
  python example_shopping_api.py --amazon-region in
  
  # Without vision analysis (faster but less detailed)
  python example_shopping_api.py --no-vision
        """
    )
    
    parser.add_argument("--image-url",
                       default="https://i.ibb.co/9ZQZ8Zq/srk-test.jpg",
                       help="Image URL to analyze")
    parser.add_argument("--movie", default="Pathaan",
                       help="Movie name")
    parser.add_argument("--amazon-region", default="com",
                       help="Amazon region (com, in, co.uk, etc.)")
    parser.add_argument("--no-vision", action="store_true",
                       help="Disable vision analysis (faster)")
    parser.add_argument("--save", action="store_true",
                       help="Save results to JSON file")
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"COMPLETE SHOPPING WORKFLOW")
    print(f"{'='*70}\n")
    
    # Step 1: Analyze image
    analysis_data = analyze_image(
        args.image_url,
        args.movie,
        enable_vision=0 if args.no_vision else 1
    )
    
    if not analysis_data:
        print("\n❌ Analysis failed. Cannot proceed with shopping.")
        return
    
    # Step 2: Get shopping recommendations
    shopping_data = get_shopping_recommendations(
        analysis_data,
        amazon_region=args.amazon_region
    )
    
    if not shopping_data:
        print("\n❌ Shopping recommendations failed.")
        return
    
    # Display results
    display_shopping_results(shopping_data)
    
    # Save if requested
    if args.save:
        filename = "shopping_results.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(shopping_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {filename}")
    
    print(f"\n{'='*70}")
    print(f"✅ WORKFLOW COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
