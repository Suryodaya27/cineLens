#!/usr/bin/env python3
"""
Simple example client for the Agentic Pipeline API.

This demonstrates how to use the API in your own applications.
"""

import requests
import json
from typing import Optional, Dict


class AgenticPipelineClient:
    """Client for the Agentic Pipeline API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client with API base URL."""
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict:
        """Check API health status."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def analyze_image(self,
                     image_url: str,
                     movie_name: str,
                     enable_vision: bool = False,
                     similarity_threshold: float = 0.6,
                     max_cast: int = 20,
                     timeout: int = 300) -> Optional[Dict]:
        """
        Analyze an image with movie context.
        
        Args:
            image_url: URL of the image to analyze
            movie_name: Name of the movie or TV series
            enable_vision: Enable detailed vision analysis (slower)
            similarity_threshold: Face matching threshold (0.0-1.0)
            max_cast: Maximum cast members to process
            timeout: Request timeout in seconds
        
        Returns:
            Analysis result dictionary or None if failed
        """
        payload = {
            "image_url": image_url,
            "movie_name": movie_name,
            "enable_vision": 1 if enable_vision else 0,
            "similarity_threshold": similarity_threshold,
            "max_cast": max_cast
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/analyze",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    
    def get_identified_people(self, result: Dict) -> list:
        """Extract identified people from analysis result."""
        if not result or not result.get('success'):
            return []
        
        people = result.get('data', {}).get('people', [])
        return [p for p in people if p.get('name')]
    
    def get_all_detections(self, result: Dict) -> Dict:
        """Extract all detections from analysis result."""
        if not result or not result.get('success'):
            return {}
        
        data = result.get('data', {})
        return {
            'people': data.get('people', []),
            'products': data.get('products', []),
            'animals': data.get('animals', []),
            'vehicles': data.get('vehicles', []),
            'electronics': data.get('electronics', []),
            'furniture': data.get('furniture', []),
            'other_objects': data.get('other_objects', [])
        }


# Example usage
def main():
    # Initialize client
    client = AgenticPipelineClient("http://localhost:8000")
    
    # Check health
    print("Checking API health...")
    health = client.health_check()
    print(f"Status: {health['status']}")
    print(f"TMDB: {'✓' if health['tmdb_configured'] else '✗'}")
    print(f"ImgBB: {'✓' if health['imgbb_configured'] else '✗'}")
    
    # Analyze an image
    print("\nAnalyzing image...")
    result = client.analyze_image(
        image_url="https://i.ibb.co/9ZQZ8Zq/srk-test.jpg",
        movie_name="Pathaan",
        enable_vision=False,  # Fast mode
        similarity_threshold=0.6
    )
    
    if result and result.get('success'):
        print(f"✓ Analysis completed in {result['processing_time']:.2f}s")
        
        # Get identified people
        people = client.get_identified_people(result)
        print(f"\nIdentified {len(people)} people:")
        for person in people:
            print(f"  • {person['name']} ({person['confidence']}%)")
            print(f"    Character: {person.get('character', 'N/A')}")
            print(f"    Crop: {person['crop_image']}")
        
        # Get all detections
        detections = client.get_all_detections(result)
        summary = result['data']['detections_summary']
        print(f"\nTotal detections:")
        print(f"  • People: {summary['people']}")
        print(f"  • Products: {summary['products']}")
        print(f"  • Animals: {summary['animals']}")
        print(f"  • Vehicles: {summary['vehicles']}")
        
        # Save full result
        with open('analysis_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\n✓ Full result saved to: analysis_result.json")
    
    else:
        print("✗ Analysis failed")


if __name__ == "__main__":
    main()
