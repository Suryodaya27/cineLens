#!/usr/bin/env python3
"""
Test to see exactly what data the shopping API receives.
"""

import requests
import json


def test_shopping_input():
    """Send a request to shopping API and check server logs for received data."""
    
    # Sample analysis data (similar to what your pipeline produces)
    analysis_data = {
        "source_image": "test_image.jpg",
        "movie_context": {
            "title": "Test Movie",
            "year": "2023"
        },
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
                        "description": "black iPhone"
                    }
                ],
                "crop_image": "https://example.com/person.jpg"
            }
        ],
        "products": [
            {
                "brand": "Nike",
                "product_type": "water bottle",
                "color": ["blue"],
                "material": "plastic",
                "crop_image": "https://example.com/bottle.jpg"
            }
        ],
        "electronics": [
            {
                "brand": "Apple",
                "model": "iPhone 14",
                "type": "smartphone",
                "color": "black",
                "crop_image": "https://example.com/phone.jpg"
            }
        ],
        "furniture": [
            {
                "type": "chair",
                "material": "wood",
                "style": "modern",
                "color": ["brown"],
                "crop_image": "https://example.com/chair.jpg"
            }
        ],
        "other_objects": [
            {
                "type": "tie",
                "brand": "Hugo Boss",
                "material": "silk",
                "color": ["red"],
                "crop_image": "https://example.com/tie.jpg"
            }
        ]
    }
    
    print("="*70)
    print("TESTING SHOPPING API INPUT DATA")
    print("="*70)
    print("Sending this analysis data to shopping API:")
    print()
    
    # Print what we're sending
    print("SENDING TO API:")
    print(f"- People: {len(analysis_data['people'])}")
    print(f"- Products: {len(analysis_data['products'])}")
    print(f"- Electronics: {len(analysis_data['electronics'])}")
    print(f"- Furniture: {len(analysis_data['furniture'])}")
    print(f"- Other objects: {len(analysis_data['other_objects'])}")
    print()
    
    # Prepare request
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 2,  # Small number for testing
        "max_visual_results": 3,
        "amazon_region": "com"
    }
    
    try:
        print("📤 Sending request to shopping API...")
        print("👀 Check the API server console/logs to see the received data details!")
        print()
        
        response = requests.post(
            "http://localhost:8000/api/shopping-recommendations",
            json=payload,
            timeout=60
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('message', 'N/A')}")
            
            data = result.get('data', {})
            metadata = data.get('metadata', {})
            
            print(f"\nResponse Summary:")
            print(f"- Total searches: {metadata.get('total_searches', 0)}")
            print(f"- Products found: {metadata.get('total_products_found', 0)}")
            
        else:
            print(f"❌ Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def test_with_your_actual_data():
    """Test with your actual Pathaan analysis data."""
    
    # Your actual data from the previous message
    your_data = {
        "source_image": "input_image_20251210_203958_413878.jpg",
        "movie_context": {
            "title": "Pathaan",
            "year": "2023",
            "cast": ["Shah Rukh Khan", "Deepika Padukone", "John Abraham"]
        },
        "people": [
            {
                "name": "Deepika Padukone",
                "gender": "female",
                "clothing": {
                    "description": "Sleeveless dark gray top paired with black shorts, casual style.",
                    "colors": ["dark gray", "black"],
                    "style": "casual",
                    "accessories": ["large hoop earrings"]
                },
                "crop_image": "https://i.ibb.co/Zz3NWZ4T/input-image-20251210-202909-662819-person-1.png"
            },
            {
                "name": "Shah Rukh Khan",
                "gender": "male",
                "clothing": {
                    "description": "White unbuttoned short-sleeved shirt, black trousers, dark suspenders over shoulders.",
                    "colors": ["white", "black", "dark"],
                    "style": "Casual yet rugged, streetwear-inspired",
                    "accessories": ["sunglasses", "gold necklace", "wristband"]
                },
                "held_items": [
                    {
                        "item": "small object",
                        "description": "Held in right hand, likely a phone or key"
                    }
                ],
                "crop_image": "https://i.ibb.co/cKjZFC3K/input-image-20251210-202909-662819-person-2.png"
            }
        ],
        "products": [],
        "electronics": [],
        "furniture": [],
        "other_objects": []
    }
    
    print("\n" + "="*70)
    print("TESTING WITH YOUR ACTUAL PATHAAN DATA")
    print("="*70)
    
    payload = {
        "analysis_data": your_data,
        "max_products_per_item": 2,
        "max_visual_results": 3,
        "amazon_region": "com"
    }
    
    try:
        print("📤 Sending your actual Pathaan data...")
        print("👀 Check the API server console to see how it processes your data!")
        print()
        
        response = requests.post(
            "http://localhost:8000/api/shopping-recommendations",
            json=payload,
            timeout=60
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('message', 'N/A')}")
        else:
            print(f"❌ Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("SHOPPING API INPUT DATA TEST")
    print("="*70)
    print("This will send data to the shopping API and show what it receives.")
    print("Make sure to check the API server console/logs for detailed input data!")
    print()
    
    # Test 1: Sample data
    test_shopping_input()
    
    # Test 2: Your actual data
    test_with_your_actual_data()
    
    print("\n" + "="*70)
    print("✅ Tests complete!")
    print("Check the API server console output to see the detailed received data.")
    print("="*70)


if __name__ == "__main__":
    main()