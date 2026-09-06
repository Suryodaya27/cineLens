#!/usr/bin/env python3
"""
TMDB Enrichment Tool
Enriches analysis JSON with actor filmography from TMDB API.
"""

import json
import requests
from typing import Dict, List, Optional
from pathlib import Path
import os

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will use environment variables directly

from logging_config import get_logger
logger = get_logger("tmdb")


class TMDBEnricher:
    """Enriches actor data with TMDB filmography."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize TMDB enricher.
        
        Args:
            api_key: TMDB API key (or set TMDB_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv('TMDB_API_KEY')
        if not self.api_key:
            raise ValueError(
                "TMDB API key required. Set TMDB_API_KEY environment variable or pass api_key parameter.\n"
                "Get free API key at: https://www.themoviedb.org/settings/api"
            )
        
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/w500"
    
    def search_person(self, name: str) -> Optional[Dict]:
        """Search for person by name on TMDB."""
        from urllib.parse import quote
        
        url = f"{self.base_url}/search/person"
        encoded_name = name
        logger.debug("searching tmdb", extra={"actor": name, "step": "search_person"})
        params = {
            'api_key': self.api_key,
            'query': encoded_name,
            'language': 'en-US'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                # Return first result (most popular)
                return data['results'][0]
            return None
        except Exception as e:
            logger.warning("tmdb person search failed", extra={"actor": name, "error": str(e), "step": "search_person"})
            return None
    
    def get_person_details(self, person_id: int) -> Optional[Dict]:
        """Get detailed person information."""
        url = f"{self.base_url}/person/{person_id}"
        params = {
            'api_key': self.api_key,
            'language': 'en-US'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("tmdb person details failed", extra={"error": str(e), "step": "get_person_details"})
            return None
    
    def get_person_credits(self, person_id: int, limit: int = 10) -> Dict:
        """Get person's movie and TV credits."""
        url = f"{self.base_url}/person/{person_id}/combined_credits"
        params = {
            'api_key': self.api_key,
            'language': 'en-US'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Sort by release date (most recent first)
            movies = sorted(
                data.get('cast', []),
                key=lambda x: x.get('release_date') or x.get('first_air_date') or '0000',
                reverse=True
            )
            
            # Format credits
            credits = []
            for movie in movies[:limit]:
                media_type = movie.get('media_type', 'movie')
                
                credit = {
                    'title': movie.get('title') or movie.get('name'),
                    'type': media_type,
                    'release_date': movie.get('release_date') or movie.get('first_air_date'),
                    'character': movie.get('character'),
                    'vote_average': movie.get('vote_average'),
                    'poster_path': f"{self.image_base_url}{movie['poster_path']}" if movie.get('poster_path') else None,
                    'tmdb_id': movie.get('id')
                }
                credits.append(credit)
            
            return {
                'total_credits': len(data.get('cast', [])),
                'recent_credits': credits
            }
        except Exception as e:
            logger.warning("tmdb credits fetch failed", extra={"error": str(e), "step": "get_person_credits"})
            return {'total_credits': 0, 'recent_credits': []}
    
    def enrich_person(self, person_data: Dict, max_credits: int = 10) -> Dict:
        """Enrich person data with TMDB information."""
        name = person_data.get('name')
        
        if not name:
            logger.warning("no name found, skipping tmdb enrichment", extra={"step": "enrich_person"})
            return person_data
        
        logger.info("searching tmdb", extra={"actor": name, "step": "enrich_person"})
        
        # Search for person
        search_result = self.search_person(name)
        if not search_result:
            logger.warning("not found on tmdb", extra={"actor": name, "step": "enrich_person"})
            person_data['tmdb_data'] = None
            return person_data
        
        person_id = search_result['id']
        logger.info("found on tmdb", extra={"actor": search_result['name'], "detail": f"ID: {person_id}", "step": "enrich_person"})
        
        # Get detailed info
        details = self.get_person_details(person_id)
        credits = self.get_person_credits(person_id, max_credits)
        
        # Build TMDB data
        tmdb_data = {
            'tmdb_id': person_id,
            'name': search_result['name'],
            'known_for_department': search_result.get('known_for_department'),
            'popularity': search_result.get('popularity'),
            'profile_image': f"{self.image_base_url}{search_result['profile_path']}" if search_result.get('profile_path') else None,
            'biography': details.get('biography') if details else None,
            'birthday': details.get('birthday') if details else None,
            'place_of_birth': details.get('place_of_birth') if details else None,
            'total_credits': credits['total_credits'],
            'recent_movies': credits['recent_credits']
        }
        
        person_data['tmdb_data'] = tmdb_data
        logger.info("enrichment done", extra={"actor": name, "count": len(credits['recent_credits']), "step": "enrich_person"})
        
        return person_data
    
    def enrich_analysis(self, analysis_file: str, output_file: str = None,
                       max_credits: int = 10) -> Dict:
        """
        Enrich complete analysis JSON with TMDB data.
        
        Args:
            analysis_file: Path to analysis JSON file
            output_file: Path to save enriched JSON (default: adds _enriched suffix)
            max_credits: Maximum number of recent credits to fetch per person
        
        Returns:
            Enriched analysis data
        """
        logger.info("tmdb enrichment started", extra={"step": "enrich_analysis", "detail": analysis_file})
        
        # Load analysis
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        logger.info("analysis loaded", extra={"step": "enrich_analysis", "detail": analysis_file})
        
        # Enrich people
        people = analysis.get('people', [])
        if not people:
            logger.warning("no people found in analysis", extra={"step": "enrich_analysis"})
            return analysis
        
        logger.info("enriching people with tmdb data", extra={"step": "enrich_analysis", "count": len(people)})
        
        for i, person in enumerate(people, 1):
            logger.info("processing person", extra={"step": "enrich_analysis", "actor": person.get('name', 'Unknown'), "detail": f"{i}/{len(people)}"})
            analysis['people'][i-1] = self.enrich_person(person, max_credits)
        
        # Save enriched analysis
        if not output_file:
            input_path = Path(analysis_file)
            output_file = input_path.parent / f"{input_path.stem}_enriched.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        logger.info("tmdb enrichment complete", extra={"step": "enrich_analysis", "detail": str(output_file)})
        
        return analysis
    
    def get_actor_filmography_summary(self, analysis_file: str) -> None:
        """Print a summary of actor filmographies."""
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        people = analysis.get('people', [])
        
        logger.info("actor filmography summary", extra={"step": "filmography_summary", "count": len(people)})
        
        for person in people:
            name = person.get('name', 'Unknown')
            tmdb_data = person.get('tmdb_data')
            
            if not tmdb_data:
                logger.warning("no tmdb data", extra={"actor": name, "step": "filmography_summary"})
                continue
            
            logger.info("actor summary", extra={
                "actor": tmdb_data['name'],
                "step": "filmography_summary",
                "detail": f"known_for={tmdb_data.get('known_for_department', 'N/A')}, total_credits={tmdb_data['total_credits']}, birthday={tmdb_data.get('birthday', 'N/A')}"
            })
            
            for i, credit in enumerate(tmdb_data['recent_movies'][:5], 1):
                title = credit['title']
                year = credit['release_date'][:4] if credit.get('release_date') else 'TBA'
                character = credit.get('character', 'N/A')
                rating = credit.get('vote_average', 0)
                
                logger.debug("credit", extra={
                    "actor": tmdb_data['name'],
                    "movie": f"{title} ({year})",
                    "detail": f"character={character}, rating={rating}/10",
                    "step": "filmography_summary"
                })


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enrich analysis JSON with TMDB actor filmography",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enrich analysis with TMDB data
  export TMDB_API_KEY=your_api_key_here
  python3 tmdb_enrichment.py final-output/image_complete_analysis.json

  # Specify output file
  python3 tmdb_enrichment.py analysis.json -o enriched.json

  # Limit to 5 recent movies per actor
  python3 tmdb_enrichment.py analysis.json --max-credits 5

  # Show filmography summary
  python3 tmdb_enrichment.py analysis_enriched.json --summary

Get TMDB API key (free): https://www.themoviedb.org/settings/api
        """
    )
    parser.add_argument("analysis_file", help="Path to analysis JSON file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--max-credits", type=int, default=10,
                       help="Maximum recent credits per person (default: 10)")
    parser.add_argument("--api-key", help="TMDB API key (or set TMDB_API_KEY env var)")
    parser.add_argument("--summary", action="store_true",
                       help="Show filmography summary (for already enriched files)")
    
    args = parser.parse_args()
    
    try:
        enricher = TMDBEnricher(args.api_key)
        
        if args.summary:
            # Just show summary
            enricher.get_actor_filmography_summary(args.analysis_file)
        else:
            # Enrich and save
            enricher.enrich_analysis(args.analysis_file, args.output, args.max_credits)
            
            # Show summary
            output_file = args.output or str(Path(args.analysis_file).parent / 
                                            f"{Path(args.analysis_file).stem}_enriched.json")
            enricher.get_actor_filmography_summary(output_file)
    
    except ValueError as e:
        logger.error("configuration error", extra={"error": str(e), "step": "main"})
        exit(1)
    except FileNotFoundError:
        logger.error("file not found", extra={"error": args.analysis_file, "step": "main"})
        exit(1)
    except Exception as e:
        logger.error("unexpected error", extra={"error": str(e), "step": "main"})
        exit(1)


if __name__ == "__main__":
    main()
