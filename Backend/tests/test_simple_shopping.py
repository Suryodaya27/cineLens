#!/usr/bin/env python3
"""
Simple test to check shopping API data with a working image URL.
"""

import requests
import json
from pprint import pprint


def test_with_working_image():
    """Test with a different image URL that should work."""
    
    # Try a different image URL
    test_images = [
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500",
        "https://via.placeholder.com/500x500.jpg",
        "https://picsum.photos/500/500"
    ]
    
    for image_url in test_images:
        print(f"\n{'='*70}")
        print(f"TESTING WITH IMAGE: {image_url}")
        print(f"{'='*70}")
        
        # Test analyze endpoint
        payload = {
            "image_url": image_url,
            "movie_name": "Test Movie",
            "enable_vision": 0,
            "similarity_threshold": 0.6
        }
        
        try:
            print("📤 Testing analyze endpoint...")
            response = requests.post("http://localhost:8000/analyze", json=payload, timeout=60)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Analysis successful!")
                
                data = result.get('data', {})
                print(f"\nData received:")
                print(f"- People: {len(data.get('people', []))}")
                print(f"- Products: {len(data.get('products', []))}")
                print(f"- Electronics: {len(data.get('electronics', []))}")
                print(f"- Furniture: {len(data.get('furniture', []))}")
                
                # Test shopping with this data
                if data:
                    test_shopping_with_data(data)
                    return True
            else:
                print(f"❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return False


def test_shopping_with_data(analysis_data):
    """Test shopping endpoint with analysis data."""
    print(f"\n{'='*50}")
    print(f"TESTING SHOPPING WITH ANALYSIS DATA")
    print(f"{'='*50}")
    
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 3,
        "max_visual_results": 5,
        "amazon_region": "com"
    }
    
    try:
        print("📤 Testing shopping endpoint...")
        response = requests.post("http://localhost:8000/api/shopping-recommendations", 
                               json=payload, timeout=120)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Shopping successful!")
            
            # Print the actual data structure
            print(f"\nSHOPPING API RESPONSE:")
            print(f"{'='*30}")
            
            data = result.get('data', {})
            
            # Print metadata
            metadata = data.get('metadata', {})
            print(f"Metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            
            # Print shopping results
            shopping_results = data.get('shopping_results', [])
            print(f"\nShopping Results ({len(shopping_results)} items):")
            
            for i, item in enumerate(shopping_results, 1):
                print(f"\n[{i}] {item.get('category', 'N/A')} - {item.get('type', 'N/A')}")
                print(f"    Search method: {item.get('search_method', 'N/A')}")
                
                if 'search_query' in item:
                    print(f"    Query: {item['search_query']}")
                
                products = item.get('products', [])
                print(f"    Products found: {len(products)}")
                
                # Show first product details
                if products:
                    product = products[0]
                    print(f"    Sample product:")
                    print(f"      Title: {product.get('title', 'N/A')[:60]}...")
                    print(f"      Price: {product.get('price', 'N/A')}")
                    print(f"      Source: {product.get('source', 'N/A')}")
            
            # Save full response
            with open('shopping_data_sample.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Full shopping response saved to: shopping_data_sample.json")
            
        else:
            print(f"❌ Shopping failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_with_mock_data():
    """Test shopping endpoint with mock analysis data."""
    print(f"\n{'='*70}")
    print(f"TESTING WITH MOCK ANALYSIS DATA")
    print(f"{'='*70}")
    
    # Create mock analysis data that should trigger shopping searches
    mock_data = {
        "people": [
            {
                "name": "Test Person",
                "gender": "male",
                "clothing": {
                    "description": "black leather jacket and blue jeans",
                    "colors": ["black", "blue"],
                    "style": "casual",
                    "accessories": ["watch", "sunglasses"]
                },
                "held_items": [
                    {
                        "item": "smartphone",
                        "description": "black smartphone"
                    }
                ]
            }
        ],
        "products": [
            {
                "brand": "Nike",
                "product_type": "water bottle",
                "color": ["blue"],
                "material": "plastic",
                "crop_image": "https://via.placeholder.com/100x100.jpg"
            }
        ],
        "electronics": [
            {
                "brand": "Apple",
                "model": "iPhone",
                "type": "smartphone",
                "color": "black",
                "crop_image": "https://via.placeholder.com/100x100.jpg"
            }
        ],
        "furniture": [
            {
                "type": "chair",
                "material": "wood",
                "style": "modern",
                "color": ["brown"],
                "crop_image": "https://via.placeholder.com/100x100.jpg"
            }
        ]
    }
    
    print("Mock data structure:")
    print(f"- People: {len(mock_data['people'])}")
    print(f"- Products: {len(mock_data['products'])}")
    print(f"- Electronics: {len(mock_data['electronics'])}")
    print(f"- Furniture: {len(mock_data['furniture'])}")
    
    test_shopping_with_data(mock_data)


def main():
    print("SIMPLE SHOPPING API TEST")
    print("="*70)
    
    # First try with working images
    success = test_with_working_image()
    
    if not success:
        print("\n⚠️  Image analysis failed. Testing with mock data instead...")
        test_with_mock_data()


if __name__ == "__main__":
    main()