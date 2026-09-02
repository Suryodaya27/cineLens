#!/usr/bin/env python3
"""
Example usage of updated_agentic_pipeline.py

This script demonstrates how to use the updated pipeline programmatically.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipelines.updated_agentic_pipeline import UpdatedAgenticPipeline
import json

def example_basic_usage():
    """Basic usage example."""
    print("Example 1: Basic Usage")
    print("=" * 70)
    
    # Initialize pipeline
    pipeline = UpdatedAgenticPipeline(yolo_model="yolov8n.pt")
    
    # Process image
    result = pipeline.process_image(
        image_path="input/srk_test.jpeg",
        movie_title="Pathaan",
        output_dir="output",
        similarity_threshold=0.6
    )
    
    # Print results
    if result:
        print("\nIdentified actors:")
        for person in result['people']:
            if person['name']:
                print(f"  - {person['name']} ({person['confidence']}%)")
                if person.get('character'):
                    print(f"    Character: {person['character']}")
    
    # Cleanup
    pipeline.close()


def example_batch_processing():
    """Batch processing example."""
    print("\nExample 2: Batch Processing")
    print("=" * 70)
    
    # Initialize pipeline once
    pipeline = UpdatedAgenticPipeline()
    
    # Process multiple images from same movie
    images = [
        "input/srk_test.jpeg",
        "input/srk_test2.jpeg",
        "input/srk_test3.jpeg"
    ]
    
    movie_title = "Pathaan"
    
    # First image will cache cast data
    # Subsequent images will be much faster
    for image_path in images:
        print(f"\nProcessing: {image_path}")
        result = pipeline.process_image(
            image_path=image_path,
            movie_title=movie_title,
            output_dir="output"
        )
        
        if result:
            identified = len([p for p in result['people'] if p['name']])
            total = len(result['people'])
            print(f"  Identified {identified}/{total} people")
    
    pipeline.close()


def example_custom_threshold():
    """Example with custom similarity threshold."""
    print("\nExample 3: Custom Similarity Threshold")
    print("=" * 70)
    
    pipeline = UpdatedAgenticPipeline()
    
    # Try different thresholds
    thresholds = [0.5, 0.6, 0.7, 0.8]
    
    for threshold in thresholds:
        print(f"\nThreshold: {threshold}")
        result = pipeline.process_image(
            image_path="input/leo_test.webp",
            movie_title="Leo",
            output_dir="output",
            similarity_threshold=threshold
        )
        
        if result:
            identified = [p for p in result['people'] if p['name']]
            print(f"  Identified: {len(identified)} people")
            for person in identified:
                print(f"    - {person['name']} ({person['confidence']}%)")
    
    pipeline.close()


def example_accessing_results():
    """Example of accessing and using results."""
    print("\nExample 4: Accessing Results")
    print("=" * 70)
    
    pipeline = UpdatedAgenticPipeline()
    
    result = pipeline.process_image(
        image_path="input/rdj.jpg",
        movie_title="Iron Man",
        output_dir="output"
    )
    
    if result:
        # Access movie context
        print(f"\nMovie: {result['movie_context']['title']}")
        print(f"Year: {result['movie_context']['year']}")
        print(f"Cast: {', '.join(result['movie_context']['cast'][:5])}")
        
        # Access detected people
        print(f"\nDetected {len(result['people'])} people:")
        for idx, person in enumerate(result['people'], 1):
            print(f"\nPerson {idx}:")
            print(f"  Name: {person['name'] or 'Unknown'}")
            print(f"  Confidence: {person['confidence']}%")
            print(f"  Crop image: {person['crop_image']}")
            
            if person.get('similarity_score'):
                print(f"  Similarity: {person['similarity_score']:.3f}")
            
            if person.get('character'):
                print(f"  Character: {person['character']}")
        
        # Save to custom location
        output_file = "my_results.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved results to: {output_file}")
    
    pipeline.close()


def example_error_handling():
    """Example with error handling."""
    print("\nExample 5: Error Handling")
    print("=" * 70)
    
    try:
        pipeline = UpdatedAgenticPipeline()
        
        # Try with non-existent movie
        result = pipeline.process_image(
            image_path="input/test.jpg",
            movie_title="NonExistentMovie12345",
            output_dir="output"
        )
        
        if result is None:
            print("Failed to process image (movie not found or no people detected)")
        
        pipeline.close()
        
    except FileNotFoundError as e:
        print(f"Error: Image file not found - {e}")
    except ValueError as e:
        print(f"Error: Configuration issue - {e}")
    except Exception as e:
        print(f"Error: {e}")


def example_prepare_cast_only():
    """Example: Just prepare cast data without processing image."""
    print("\nExample 6: Prepare Cast Data Only")
    print("=" * 70)
    
    pipeline = UpdatedAgenticPipeline()
    
    # Pre-cache cast data for multiple movies
    movies = ["Pathaan", "Jawan", "Leo", "Iron Man"]
    
    for movie in movies:
        print(f"\nPreparing cast for: {movie}")
        movie_context = pipeline.prepare_movie_cast(
            movie_title=movie,
            max_cast=15,
            images_per_actor=3
        )
        
        if movie_context:
            print(f"  ✓ Cached {len(movie_context['cast'])} cast members")
        else:
            print(f"  ✗ Failed to prepare cast")
    
    print("\nCast data is now cached for fast processing!")
    pipeline.close()


if __name__ == "__main__":
    # Run examples
    print("Updated Agentic Pipeline - Usage Examples")
    print("=" * 70)
    print()
    
    # Uncomment the examples you want to run:
    
    # example_basic_usage()
    # example_batch_processing()
    # example_custom_threshold()
    # example_accessing_results()
    # example_error_handling()
    # example_prepare_cast_only()
    
    print("\nTo run examples, uncomment them in the __main__ section.")
    print("Make sure you have:")
    print("  1. PostgreSQL running with pgvector")
    print("  2. TMDB_API_KEY environment variable set")
    print("  3. Required Python packages installed")
    print("\nSee UPDATED_PIPELINE_SETUP.md for setup instructions.")
