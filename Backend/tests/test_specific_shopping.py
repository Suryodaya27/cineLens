#!/usr/bin/env python3
"""
Test shopping API with the specific analysis data provided.
"""

import requests
import json
from pprint import pprint


def test_shopping_with_your_data():
    """Test shopping endpoint with your specific analysis data."""
    
    # Your actual analysis data
    analysis_data = {
        "source_image": "input_image_20251210_203958_413878.jpg",
        "movie_context": {
            "title": "Pathaan",
            "year": "2023",
            "cast": ["Shah Rukh Khan", "Deepika Padukone", "John Abraham", "Dimple Kapadia", "Ashutosh Rana", "Akash Bhatija", "Prakash Belawadi", "Viraf Patel", "Shaji Choudhary", "Salman Khan"]
        },
        "scene_analysis": {
            "setting": "Outdoor, public space (likely a plaza or street)",
            "lighting": "Bright, natural sunlight with strong highlights and defined shadows, indicating direct overhead lighting",
            "time_of_day": "Midday or early afternoon (based on bright, direct sunlight and minimal long shadows)",
            "mood": "Stylish, confident, and energetic (conveyed by posed postures, fashionable attire, and vibrant lighting)",
            "background_elements": "Blurred architectural structures and indistinct figures in the distance, suggesting an urban environment",
            "composition": "Two subjects positioned side-by-side with balanced framing; the male subject on the left and female subject on the right, each occupying distinct visual space while maintaining a cohesive, staged arrangement",
            "context": "Fashion or commercial photoshoot, likely for promoting clothing or lifestyle branding, indicated by the stylized attire and posed positioning"
        },
        "detections_summary": {
            "people": 2,
            "products": 0,
            "animals": 0,
            "vehicles": 0,
            "electronics": 0,
            "furniture": 0,
            "other_objects": 0
        },
        "people": [
            {
                "name": "Deepika Padukone",
                "profession": "Actor",
                "character": "Rubina Mohsin",
                "confidence": 62,
                "similarity_score": 0.6274762067654085,
                "matched_image": "cache/tmdb/actors/actor_53975_Deepika_Padukone/profile_4.jpg",
                "gender": "female",
                "facial_features": "Long, wavy brown hair cascading over shoulders. Dark, almond-shaped eyes. Medium facial structure with a defined jawline and tan skin tone. Large hoop earrings.",
                "clothing": {
                    "description": "Sleeveless dark gray top paired with black shorts, casual style.",
                    "colors": ["dark gray", "black"],
                    "style": "casual",
                    "accessories": ["large hoop earrings"]
                },
                "pose": "Standing with one hand on hip, turned slightly to the side, showcasing the outfit.",
                "expression": "Neutral to slightly serious expression, looking directly at the camera.",
                "held_items": [],
                "object_class": "person",
                "crop_image": "https://i.ibb.co/Zz3NWZ4T/input-image-20251210-202909-662819-person-1.png",
                "detection_confidence": 0.709444522857666,
                "crop_image_hosted": True
            },
            {
                "name": "Shah Rukh Khan",
                "profession": "Actor",
                "character": "Pathaan",
                "confidence": 52,
                "similarity_score": 0.5262877410940434,
                "matched_image": "cache/tmdb/actors/actor_35742_Shah_Rukh_Khan/profile_3.jpg",
                "gender": "male",
                "facial_features": "Long, wavy dark hair. Face with strong jawline and masculine features. Eyes covered by sunglasses, so no visible eye detail. Prominent cheekbones and rugged facial structure.",
                "clothing": {
                    "description": "White unbuttoned short-sleeved shirt, black trousers, dark suspenders over shoulders. Open collar revealing chest.",
                    "colors": ["white", "black", "dark"],
                    "style": "Casual yet rugged, streetwear-inspired",
                    "accessories": ["sunglasses", "gold necklace", "wristband"]
                },
                "pose": "Standing upright with one hand in pocket and the other hanging naturally by the side, suggesting a confident stride.",
                "expression": "Due to sunglasses, facial expression is partially obscured, but overall demeanor appears cool and confident.",
                "held_items": [
                    {
                        "item": "small object",
                        "description": "Held in right hand, likely a phone or key"
                    }
                ],
                "object_class": "person",
                "crop_image": "https://i.ibb.co/cKjZFC3K/input-image-20251210-202909-662819-person-2.png",
                "detection_confidence": 0.7037045359611511,
                "crop_image_hosted": True
            }
        ],
        "products": [],
        "animals": [],
        "vehicles": [],
        "electronics": [],
        "furniture": [],
        "other_objects": []
    }
    
    print("="*70)
    print("TESTING SHOPPING API WITH YOUR ANALYSIS DATA")
    print("="*70)
    
    # Print what should be searchable from this data
    print("Analysis Summary:")
    print(f"- People: {len(analysis_data['people'])}")
    print(f"- Products: {len(analysis_data['products'])}")
    print(f"- Electronics: {len(analysis_data['electronics'])}")
    print(f"- Furniture: {len(analysis_data['furniture'])}")
    print()
    
    print("Expected Searchable Items:")
    for person in analysis_data['people']:
        print(f"- {person['name']} ({person['gender']}):")
        clothing = person['clothing']
        print(f"  - Clothing: {clothing['description']}")
        print(f"  - Colors: {clothing['colors']}")
        print(f"  - Accessories: {clothing['accessories']}")
        if person['held_items']:
            for item in person['held_items']:
                print(f"  - Held item: {item['item']} - {item['description']}")
    print()
    
    # Test the shopping endpoint
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 3,  # Limit for faster testing
        "max_visual_results": 5,
        "amazon_region": "com"
    }
    
    try:
        print("📤 Sending shopping request...")
        print("⏱️  This may take 30-60 seconds...")
        
        response = requests.post(
            "http://localhost:8000/api/shopping-recommendations", 
            json=payload, 
            timeout=180  # 3 minutes timeout
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Shopping recommendations successful!")
            
            # Print the response structure
            print(f"\nRESPONSE STRUCTURE:")
            print(f"- Success: {result.get('success')}")
            print(f"- Message: {result.get('message')}")
            
            data = result.get('data', {})
            
            # Print metadata
            metadata = data.get('metadata', {})
            print(f"\nMETADATA:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            
            # Print shopping results in detail
            shopping_results = data.get('shopping_results', [])
            print(f"\nSHOPPING RESULTS ({len(shopping_results)} items):")
            print("="*50)
            
            for i, item in enumerate(shopping_results, 1):
                print(f"\n[{i}] CATEGORY: {item.get('category', 'N/A').upper()}")
                print(f"    Type: {item.get('type', 'N/A')}")
                print(f"    Search Method: {item.get('search_method', 'N/A')}")
                
                if 'search_query' in item:
                    print(f"    Search Query: '{item['search_query']}'")
                
                products = item.get('products', [])
                print(f"    Products Found: {len(products)}")
                
                # Show product details
                for j, product in enumerate(products[:2], 1):  # Show first 2 products
                    print(f"\n    Product {j}:")
                    print(f"      Title: {product.get('title', 'N/A')}")
                    print(f"      Price: {product.get('price', 'N/A')}")
                    print(f"      Rating: {product.get('rating', 'N/A')}")
                    print(f"      Source: {product.get('source', 'N/A')}")
                    if product.get('url'):
                        print(f"      URL: {product['url']}")
                
                if len(products) > 2:
                    print(f"    ... and {len(products) - 2} more products")
            
            # Save the full response
            with open('shopping_response_full.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Full response saved to: shopping_response_full.json")
            
            return True
            
        else:
            print(f"❌ Shopping failed:")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏱️  Request timed out. The shopping API is taking too long.")
        print(f"This could be due to:")
        print(f"- Amazon rate limiting")
        print(f"- SerpAPI rate limiting") 
        print(f"- Network issues")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_amazon_directly():
    """Test Amazon scraping directly with the clothing from your data."""
    print(f"\n{'='*70}")
    print(f"TESTING AMAZON SCRAPING DIRECTLY")
    print(f"{'='*70}")
    
    try:
        from amazon_shopping import AmazonShopper
        
        shopper = AmazonShopper("com")
        
        # Test queries based on your data
        test_queries = [
            "female dark gray sleeveless top",
            "female black shorts casual",
            "large hoop earrings women",
            "male white unbuttoned shirt",
            "male black trousers",
            "dark suspenders men",
            "sunglasses men",
            "gold necklace men"
        ]
        
        for query in test_queries[:3]:  # Test first 3 to avoid rate limiting
            print(f"\nTesting: {query}")
            products = shopper.search_amazon(query, max_results=2)
            
            if products:
                for i, product in enumerate(products, 1):
                    print(f"  {i}. {product.get('title', 'N/A')[:60]}...")
                    print(f"     Price: {product.get('price', 'N/A')}")
                    print(f"     Rating: {product.get('rating', 'N/A')}")
            else:
                print(f"  No products found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("TESTING SHOPPING API WITH YOUR SPECIFIC DATA")
    print("="*70)
    
    # Test with your actual data
    success = test_shopping_with_your_data()
    
    if not success:
        print(f"\n⚠️  API test failed. Testing Amazon scraping directly...")
        test_amazon_directly()


if __name__ == "__main__":
    main()