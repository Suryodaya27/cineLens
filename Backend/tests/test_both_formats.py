#!/usr/bin/env python3
"""
Test both correct and wrong data formats for shopping API.
"""

import requests
import json


def test_correct_format():
    """Test with correct format (direct analysis data)."""
    print("="*70)
    print("TESTING CORRECT FORMAT (Direct Analysis Data)")
    print("="*70)
    
    # Bruce Almighty data (correct format)
    analysis_data = {
        'source_image': 'input_image_20251210_105418_959921.jpg',
        'movie_context': {
            'title': 'Bruce Almighty',
            'year': '2003',
            'cast': ['Jim Carrey', 'Morgan Freeman', 'Jennifer Aniston']
        },
        'people': [
            {
                'name': 'Jim Carrey',
                'gender': 'male',
                'clothing': {
                    'description': 'Plaid button-up shirt over a white t-shirt',
                    'colors': ['gray', 'blue', 'white'],
                    'style': 'Casual',
                    'accessories': []
                }
            },
            {
                'name': 'Morgan Freeman',
                'gender': 'male',
                'clothing': {
                    'description': 'White suit jacket over a white dress shirt with a white tie',
                    'colors': ['white'],
                    'style': 'formal business attire',
                    'accessories': []
                }
            }
        ],
        'products': [],
        'electronics': [],
        'furniture': [],
        'other_objects': []
    }
    
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 2,
        "max_visual_results": 3,
        "amazon_region": "in"
    }
    
    try:
        print("📤 Sending correct format...")
        response = requests.post(
            "http://localhost:8000/api/shopping-recommendations",
            json=payload,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('message')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")


def test_wrong_format():
    """Test with wrong format (full API response)."""
    print("\n" + "="*70)
    print("TESTING WRONG FORMAT (Full API Response)")
    print("="*70)
    
    # Ra.One data (wrong format - full API response)
    analysis_data = {
        'success': True,
        'message': 'Image analyzed successfully',
        'analysis_data': {
            'source_image': 'input_image_20251210_210834_211917.jpg',
            'movie_context': {
                'title': 'Ra.One',
                'year': '2011',
                'cast': ['Shah Rukh Khan', 'Arjun Rampal', 'Kareena Kapoor Khan']
            },
            'people': [
                {
                    'name': 'Shah Rukh Khan',
                    'gender': 'male',
                    'clothing': {
                        'object': 'futuristic armored suit',
                        'colors': ['blue', 'black'],
                        'style': 'tight-fitting, armored, with blue accents',
                        'accessories': ['glowing belt elements']
                    }
                }
            ],
            'products': [],
            'electronics': [],
            'furniture': [],
            'other_objects': []
        },
        'processing_time': 48.109759
    }
    
    payload = {
        "analysis_data": analysis_data,
        "max_products_per_item": 2,
        "max_visual_results": 3,
        "amazon_region": "in"
    }
    
    try:
        print("📤 Sending wrong format (should be fixed now)...")
        response = requests.post(
            "http://localhost:8000/api/shopping-recommendations",
            json=payload,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('message')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")


def main():
    print("TESTING BOTH DATA FORMATS FOR SHOPPING API")
    print("="*70)
    print("This will test both correct and wrong data formats.")
    print("The API should now handle both formats correctly.")
    print()
    
    # Test correct format
    test_correct_format()
    
    # Test wrong format (should work now)
    test_wrong_format()
    
    print("\n" + "="*70)
    print("✅ Both tests complete!")
    print("Check the API server console to see how it handles each format.")
    print("="*70)


if __name__ == "__main__":
    main()