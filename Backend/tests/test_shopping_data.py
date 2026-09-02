#!/usr/bin/env python3
"""
Test script to print actual data received from shopping API endpoints.
This will help debug what data is being returned from the shopping APIs.
"""

import requests
import json
import sys
from pprint import pprint


def test_health_endpoint():
    """Test the health endpoint to see if API is running."""
    print("="*70)
    print("TESTING HEALTH ENDPOINT")
    print("="*70)
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Health Check Response:")
            pprint(data)
            return True
        else:
            print(f"Health check failed: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("Make sure the API server is running with: python api.py")
        return False


def test_analyze_endpoint():
    """Test the analyze endpoint with a sample image."""
    print("\n" + "="*70)
    print("TESTING ANALYZE ENDPOINT")
    print("="*70)
    
    # Sample request
    payload = {
        "image_url": "https://i.ibb.co/9ZQZ8Zq/srk-test.jpg",
        "movie_name": "Pathaan",
        "enable_vision": 0,  # Disable vision for faster testing
        "similarity_threshold": 0.6
    }
    
    print(f"Request payload:")
    pprint(payload)
    print()
    
    try:
        print("📤 Sending analyze request...")
        response = requests.post("http://localhost:8000/analyze", json=payload, timeout=300)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Analysis successful!")
            print(f"Processing time: {result.get('processing_time', 'N/A')}s")
            
            # Print structure of returned data
            data = result.get('data', {})
            print(f"\nAnalysis Data Structure:")
            print(f"- People: {len(data.get('people', []))}")
            print(f"- Products: {len(data.get('products', []))}")
            print(f"- Electronics: {len(data.get('electronics', []))}")
            print(f"- Furniture: {len(data.get('furniture', []))}")
            print(f"- Other Objects: {len(data.get('other_objects', []))}")
            
            # Print sample data from each category
            print(f"\nSample Data from Analysis:")
            
            if data.get('people'):
                print(f"\nPeople[0] sample:")
                person = data['people'][0]
                print(f"  Name: {person.get('name', 'N/A')}")
                print(f"  Gender: {person.get('gender', 'N/A')}")
                clothing = person.get('clothing', {})
                print(f"  Clothing description: {clothing.get('description', 'N/A')}")
                print(f"  Clothing colors: {clothing.get('colors', [])}")
                print(f"  Accessories: {clothing.get('accessories', [])}")
            
            if data.get('products'):
                print(f"\nProducts[0] sample:")
                product = data['products'][0]
                print(f"  Brand: {product.get('brand', 'N/A')}")
                print(f"  Type: {product.get('product_type', 'N/A')}")
                print(f"  Color: {product.get('color', 'N/A')}")
                print(f"  Crop image: {product.get('crop_image', 'N/A')}")
            
            return data
        else:
            print(f"❌ Analysis failed: {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_shopping_endpoint(analysis_data):
    """Test the shopping recommendations endpoint."""
    print("\n" + "="*70)
    print("TESTING SHOPPING RECOMMENDATIONS ENDPOINT")
    print("="*70)
    
    if not analysis_data:
        print("❌ No analysis data provided. Cannot test shopping endpoint.")
        return None
    
    # Sample shopping request
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 3,  # Limit for testing
        "max_visual_results": 5,     # Limit for testing
        "amazon_region": "com"
    }
    
    print(f"Request payload structure:")
    print(f"- Analysis data keys: {list(analysis_data.keys())}")
    print(f"- Max products per item: {payload['max_products_per_item']}")
    print(f"- Max visual results: {payload['max_visual_results']}")
    print(f"- Amazon region: {payload['amazon_region']}")
    print()
    
    try:
        print("📤 Sending shopping request...")
        response = requests.post("http://localhost:8000/api/shopping-recommendations", 
                               json=payload, timeout=300)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Shopping recommendations successful!")
            
            # Print the complete response structure
            print(f"\nShopping Response Structure:")
            print(f"- Success: {result.get('success')}")
            print(f"- Message: {result.get('message')}")
            
            data = result.get('data', {})
            print(f"\nShopping Data Structure:")
            print(f"- Shopping results: {len(data.get('shopping_results', []))}")
            
            metadata = data.get('metadata', {})
            print(f"- Metadata:")
            print(f"  - Total searches: {metadata.get('total_searches', 0)}")
            print(f"  - Text searches: {metadata.get('text_searches', 0)}")
            print(f"  - Visual searches: {metadata.get('visual_searches', 0)}")
            print(f"  - Total products found: {metadata.get('total_products_found', 0)}")
            
            # Print detailed shopping results
            shopping_results = data.get('shopping_results', [])
            
            print(f"\nDETAILED SHOPPING RESULTS:")
            print("="*50)
            
            for i, result_item in enumerate(shopping_results, 1):
                print(f"\n[{i}] Category: {result_item.get('category', 'N/A')}")
                print(f"    Type: {result_item.get('type', 'N/A')}")
                print(f"    Search method: {result_item.get('search_method', 'N/A')}")
                
                if result_item.get('search_query'):
                    print(f"    Search query: {result_item['search_query']}")
                
                products = result_item.get('products', [])
                print(f"    Products found: {len(products)}")
                
                # Print first few products
                for j, product in enumerate(products[:2], 1):
                    print(f"\n    Product {j}:")
                    print(f"      Title: {product.get('title', 'N/A')[:80]}...")
                    print(f"      Price: {product.get('price', 'N/A')}")
                    print(f"      Rating: {product.get('rating', 'N/A')}")
                    print(f"      Source: {product.get('source', 'N/A')}")
                    if product.get('url'):
                        print(f"      URL: {product['url'][:60]}...")
                
                if len(products) > 2:
                    print(f"    ... and {len(products) - 2} more products")
            
            # Save full response for detailed inspection
            with open('shopping_response_debug.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Full response saved to: shopping_response_debug.json")
            
            return data
        else:
            print(f"❌ Shopping failed: {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_amazon_scraping():
    """Test Amazon scraping directly."""
    print("\n" + "="*70)
    print("TESTING AMAZON SCRAPING DIRECTLY")
    print("="*70)
    
    try:
        from amazon_shopping import AmazonShopper
        
        shopper = AmazonShopper("com")
        
        # Test a simple search
        test_query = "black leather jacket men"
        print(f"Testing Amazon search for: {test_query}")
        
        products = shopper.search_amazon(test_query, max_results=3)
        
        print(f"Found {len(products)} products:")
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.get('title', 'N/A')[:60]}...")
            print(f"   Price: {product.get('price', 'N/A')}")
            print(f"   Rating: {product.get('rating', 'N/A')}")
            print(f"   Source: {product.get('source', 'N/A')}")
        
        return len(products) > 0
    
    except Exception as e:
        print(f"❌ Error testing Amazon scraping: {e}")
        return False


def test_visual_search():
    """Test visual search directly."""
    print("\n" + "="*70)
    print("TESTING VISUAL SEARCH DIRECTLY")
    print("="*70)
    
    try:
        from visual_search import VisualSearcher
        
        # Check if API keys are configured
        import os
        serpapi_key = os.getenv('SERPAPI_KEY')
        imgbb_key = os.getenv('IMGBB_API_KEY')
        
        print(f"SERPAPI_KEY configured: {'✓' if serpapi_key else '✗'}")
        print(f"IMGBB_API_KEY configured: {'✓' if imgbb_key else '✗'}")
        
        if not serpapi_key:
            print("❌ SERPAPI_KEY not configured. Visual search will not work.")
            return False
        
        if not imgbb_key:
            print("⚠️  IMGBB_API_KEY not configured. Visual search may not work.")
        
        searcher = VisualSearcher("serpapi")
        
        # Test with a sample image URL
        test_image_url = "https://i.ibb.co/9ZQZ8Zq/srk-test.jpg"
        print(f"Testing visual search with: {test_image_url}")
        
        products = searcher.search_by_image(test_image_url, max_results=3)
        
        print(f"Found {len(products)} visually similar products:")
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.get('title', 'N/A')[:60]}...")
            print(f"   Source: {product.get('source', 'N/A')}")
            print(f"   Link: {product.get('link', 'N/A')[:60]}...")
        
        return len(products) > 0
    
    except Exception as e:
        print(f"❌ Error testing visual search: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("SHOPPING API DATA TESTING")
    print("="*70)
    print("This script will test all shopping-related endpoints and print the actual data received.")
    print()
    
    # Test 1: Health check
    if not test_health_endpoint():
        print("\n❌ API server is not running. Please start it with: python api.py")
        sys.exit(1)
    
    # Test 2: Analyze endpoint
    analysis_data = test_analyze_endpoint()
    
    # Test 3: Shopping endpoint (if analysis worked)
    if analysis_data:
        shopping_data = test_shopping_endpoint(analysis_data)
    
    # Test 4: Direct Amazon scraping
    amazon_works = test_amazon_scraping()
    
    # Test 5: Direct visual search
    visual_works = test_visual_search()
    
    # Summary
    print("\n" + "="*70)
    print("TESTING SUMMARY")
    print("="*70)
    print(f"✅ API Health: Working")
    print(f"{'✅' if analysis_data else '❌'} Analysis Endpoint: {'Working' if analysis_data else 'Failed'}")
    print(f"{'✅' if 'shopping_data' in locals() and shopping_data else '❌'} Shopping Endpoint: {'Working' if 'shopping_data' in locals() and shopping_data else 'Failed'}")
    print(f"{'✅' if amazon_works else '❌'} Amazon Scraping: {'Working' if amazon_works else 'Failed'}")
    print(f"{'✅' if visual_works else '❌'} Visual Search: {'Working' if visual_works else 'Failed'}")
    
    print(f"\n💾 Check shopping_response_debug.json for full API response details")


if __name__ == "__main__":
    main()