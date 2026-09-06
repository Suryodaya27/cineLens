#!/usr/bin/env python3
"""
Visual Search Integration
Uses actual cropped images to find similar products.
Supports: Google Lens API, SerpAPI, and local alternatives.
"""

import json
import requests
import base64
from pathlib import Path
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

from logging_config import get_logger
logger = get_logger("visual_search")


class VisualSearcher:
    """Visual search using cropped images."""
    
    def __init__(self, provider: str = "serpapi", location: str = None, country: str = None):
        """
        Initialize visual searcher.
        
        Args:
            provider: 'serpapi' (recommended), 'google-lens', or 'bing-visual'
            location: Location for search results (e.g., "Mumbai, India", "Delhi, India")
            country: Country code for search results (e.g., "in" for India, "us" for USA)
        """
        self.provider = provider.lower()
        self.location = location
        self.country = country or ("in" if location and "india" in location.lower() else None)
        
        if self.provider == "serpapi":
            self.api_key = os.getenv('SERPAPI_KEY')
            if not self.api_key:
                raise ValueError(
                    "SerpAPI key required. Set SERPAPI_KEY in .env file.\n"
                    "Get free API key at: https://serpapi.com/users/sign_up"
                )
            # Strip any whitespace
            self.api_key = self.api_key.strip()
            
            # ImgBB API key for image hosting
            self.imgbb_key = os.getenv('IMGBB_API_KEY')
            if not self.imgbb_key:
                logger.warning("IMGBB_API_KEY not set, visual search may not work without it", extra={"step": "init"})
        elif self.provider == "google-lens":
            # Google Lens API (if available)
            self.api_key = os.getenv('GOOGLE_API_KEY')
        elif self.provider == "bing-visual":
            # Bing Visual Search API
            self.api_key = os.getenv('BING_API_KEY')
    
    def search_by_image(self, image_path: str, max_results: int = 10) -> List[Dict]:
        """
        Search for similar products using image.
        
        Args:
            image_path: Path to cropped image
            max_results: Maximum results to return
        
        Returns:
            List of similar products
        """
        if self.provider == "serpapi":
            return self._search_serpapi(image_path, max_results)
        elif self.provider == "google-lens":
            return self._search_google_lens(image_path, max_results)
        elif self.provider == "bing-visual":
            return self._search_bing(image_path, max_results)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _upload_to_imgbb(self, image_path: str) -> Optional[str]:
        """
        Upload image to ImgBB and get public URL.
        
        Args:
            image_path: Local image path
            
        Returns:
            Public URL or None if failed
        """
        if not self.imgbb_key:
            logger.warning("imgbb api key not configured", extra={"step": "upload_imgbb"})
            return None
        
        try:
            import requests
            
            # ImgBB upload endpoint
            url = "https://api.imgbb.com/1/upload"
            
            # Read image and encode to base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Upload
            payload = {
                'key': self.imgbb_key,
                'image': image_data
            }
            
            response = requests.post(url, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    image_url = result['data']['url']
                    logger.info("uploaded to imgbb", extra={"step": "upload_imgbb", "detail": image_url[:50]})
                    return image_url
            
            logger.warning("imgbb upload failed", extra={"step": "upload_imgbb", "error": response.text[:100]})
            return None
            
        except Exception as e:
            logger.warning("imgbb upload error", extra={"step": "upload_imgbb", "error": str(e)})
            return None
    
    def _search_serpapi(self, image_path: str, max_results: int) -> List[Dict]:
        """Search using SerpAPI Google Lens."""
        image_label = Path(image_path).name if not image_path.startswith('http') else image_path[:50] + '...'
        logger.info("visual search started", extra={"step": "search_serpapi", "detail": image_label})
        
        try:
            import requests
            
            # Check if image_path is already a URL
            if image_path.startswith('http://') or image_path.startswith('https://'):
                logger.info("using provided url", extra={"step": "search_serpapi"})
                image_url = image_path
            else:
                # Step 1: Upload local image to ImgBB to get public URL
                logger.info("uploading image to imgbb", extra={"step": "search_serpapi"})
                image_url = self._upload_to_imgbb(image_path)
                
                if not image_url:
                    logger.warning("cannot proceed without public image url", extra={"step": "search_serpapi"})
                    return []
            
            # Step 2: Use public URL with SerpAPI Google Lens
            logger.info("searching with google lens via serpapi", extra={"step": "search_serpapi"})
            
            params = {
                'engine': 'google_lens',
                'url': image_url,  # Public URL from ImgBB
                'api_key': self.api_key
            }
            
            # Add location/country parameters if specified
            if self.location:
                params['location'] = self.location
                logger.debug("location set", extra={"step": "search_serpapi", "detail": self.location})
            
            if self.country:
                params['gl'] = self.country  # Google country code
                params['hl'] = self.country  # Language code
                logger.debug("country set", extra={"step": "search_serpapi", "detail": self.country})
            
            response = requests.get('https://serpapi.com/search.json', 
                                   params=params, 
                                   timeout=60)
            
            # Check response
            if response.status_code != 200:
                logger.warning("serpapi error", extra={"step": "search_serpapi", "error": f"status {response.status_code}: {response.text[:300]}"})
                return []
            
            try:
                results = response.json()
            except Exception:
                logger.warning("invalid json response from serpapi", extra={"step": "search_serpapi", "error": response.text[:300]})
                return []
            
            # Debug: Check if there's an error
            if 'error' in results:
                logger.warning("serpapi returned error", extra={"step": "search_serpapi", "error": results['error']})
                return []
            
            # Parse results
            products = []
            
            # Visual matches
            visual_matches = results.get('visual_matches', [])
            if not visual_matches:
                available_keys = list(results.keys())
                logger.info("no visual matches found", extra={"step": "search_serpapi", "detail": f"available_keys={available_keys[:10]}"})
            
            for match in visual_matches[:max_results]:
                product = {
                    'title': match.get('title', ''),
                    'link': match.get('link', ''),
                    'source': match.get('source', ''),
                    'price': match.get('price', {}).get('value') if match.get('price') else None,
                    'thumbnail': match.get('thumbnail', ''),
                    'similarity': 'high',
                    'search_type': 'visual'
                }
                products.append(product)
            
            if products:
                logger.info("visual matches found", extra={"step": "search_serpapi", "count": len(products)})
            return products
        
        except Exception as e:
            import traceback
            logger.error("visual search error", extra={"step": "search_serpapi", "error": str(e), "detail": traceback.format_exc()})
            return []
    
    def _upload_image_to_url(self, image_path: str) -> str:
        """
        Convert local image to base64 data URL for SerpAPI.
        SerpAPI accepts: URL, base64, or file upload.
        """
        import base64
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Determine image type
        ext = Path(image_path).suffix.lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')
        
        return f"data:{mime_type};base64,{image_data}"
    
    def _search_google_lens(self, image_path: str, max_results: int) -> List[Dict]:
        """Search using Google Lens API (if available)."""
        logger.warning("google lens api not implemented, use serpapi instead", extra={"step": "search_google_lens"})
        return []
    
    def _search_bing(self, image_path: str, max_results: int) -> List[Dict]:
        """Search using Bing Visual Search API."""
        logger.info("bing visual search started", extra={"step": "search_bing", "detail": Path(image_path).name})
        
        try:
            url = "https://api.bing.microsoft.com/v7.0/images/visualsearch"
            
            with open(image_path, 'rb') as f:
                files = {'image': f}
                headers = {'Ocp-Apim-Subscription-Key': self.api_key}
                
                response = requests.post(url, headers=headers, files=files, timeout=30)
                response.raise_for_status()
                data = response.json()
            
            # Parse Bing results
            products = []
            tags = data.get('tags', [])
            
            for tag in tags:
                actions = tag.get('actions', [])
                for action in actions:
                    if action.get('actionType') == 'ProductVisualSearch':
                        for item in action.get('data', {}).get('value', [])[:max_results]:
                            product = {
                                'title': item.get('name', ''),
                                'link': item.get('hostPageUrl', ''),
                                'source': item.get('hostPageDisplayUrl', ''),
                                'price': item.get('price', {}).get('value'),
                                'thumbnail': item.get('thumbnailUrl', ''),
                                'similarity': 'high',
                                'search_type': 'visual'
                            }
                            products.append(product)
            
            logger.info("bing visual search complete", extra={"step": "search_bing", "count": len(products)})
            return products
        
        except Exception as e:
            logger.warning("bing visual search failed", extra={"step": "search_bing", "error": str(e)})
            return []
    
    def enrich_with_visual_search(self, analysis_file: str, output_file: str = None,
                                  max_results_per_item: int = 10) -> Dict:
        """
        Add visual search results to analysis.
        
        Args:
            analysis_file: Path to analysis JSON (with crops)
            output_file: Output path
            max_results_per_item: Max results per crop
        
        Returns:
            Enriched analysis
        """
        logger.info("visual search integration started", extra={"step": "enrich", "detail": analysis_file})
        
        # Load analysis
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        logger.info("analysis loaded, skipping people crops (would match faces not clothes)", extra={"step": "enrich", "detail": analysis_file})
        
        # Collect all crop images (following output_schema.json structure)
        crops_to_search = []
        
        # SKIP people crops - Google Lens will match faces, not clothing
        # For clothing, use Amazon shopping (text-based search works better)
        
        # 1. Products (bottles, cups, etc.) - from schema
        for idx, product in enumerate(analysis.get('products', []), 1):
            crop_path = product.get('crop_image')
            if crop_path and Path(crop_path).exists():
                # Build description from schema fields
                brand = product.get('brand', '')
                product_type = product.get('product_type', 'product')
                colors = product.get('color', [])
                
                desc_parts = []
                if brand and brand not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(brand)
                desc_parts.append(product_type)
                if colors and isinstance(colors, list) and len(colors) > 0:
                    desc_parts.append(colors[0])
                
                description = ' '.join(desc_parts)
                
                crops_to_search.append({
                    'path': crop_path,
                    'category': 'product',
                    'index': idx,
                    'description': description,
                    'data': product
                })
        
        # 2. Electronics - from schema
        for idx, electronic in enumerate(analysis.get('electronics', []), 1):
            crop_path = electronic.get('crop_image')
            if crop_path and Path(crop_path).exists():
                # Build description from schema fields
                brand = electronic.get('brand', '')
                model = electronic.get('model', '')
                elec_type = electronic.get('type', 'electronic')
                
                desc_parts = []
                if brand and brand not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(brand)
                if model and model not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(model)
                desc_parts.append(elec_type)
                
                description = ' '.join(desc_parts)
                
                crops_to_search.append({
                    'path': crop_path,
                    'category': 'electronics',
                    'index': idx,
                    'description': description,
                    'data': electronic
                })
        
        # 3. Furniture - from schema
        for idx, furniture in enumerate(analysis.get('furniture', []), 1):
            crop_path = furniture.get('crop_image')
            if crop_path and Path(crop_path).exists():
                # Build description from schema fields
                furn_type = furniture.get('type', 'furniture')
                material = furniture.get('material', '')
                style = furniture.get('style', '')
                
                desc_parts = [furn_type]
                if material and material not in ['unknown', 'unclear']:
                    desc_parts.append(material)
                if style and style not in ['unknown', 'unclear']:
                    desc_parts.append(style)
                
                description = ' '.join(desc_parts)
                
                crops_to_search.append({
                    'path': crop_path,
                    'category': 'furniture',
                    'index': idx,
                    'description': description,
                    'data': furniture
                })
        
        # 4. Other objects (ties, accessories, etc.) - from schema
        for idx, obj in enumerate(analysis.get('other_objects', []), 1):
            crop_path = obj.get('crop_image')
            if crop_path and Path(crop_path).exists():
                # Build description from schema fields
                obj_type = obj.get('type', 'object')
                brand = obj.get('brand', '')
                colors = obj.get('color', [])
                material = obj.get('material', '')
                
                desc_parts = []
                if brand and brand not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(brand)
                desc_parts.append(obj_type)
                if material and material not in ['unknown', 'unclear']:
                    desc_parts.append(material)
                if colors and isinstance(colors, list) and len(colors) > 0:
                    desc_parts.append(colors[0])
                
                description = ' '.join(desc_parts)
                
                crops_to_search.append({
                    'path': crop_path,
                    'category': 'other_object',
                    'index': idx,
                    'description': description,
                    'data': obj
                })
        
        if not crops_to_search:
            logger.warning("no crop images found", extra={"step": "enrich"})
            return analysis
        
        logger.info("crops found for visual search", extra={"step": "enrich", "count": len(crops_to_search)})
        
        # Visual search for each crop
        visual_results = []
        
        for i, crop in enumerate(crops_to_search, 1):
            logger.info("processing crop", extra={"step": "enrich", "detail": f"{crop['category']}: {crop['description']} ({i}/{len(crops_to_search)})"})
            
            # Search by image
            products = self.search_by_image(crop['path'], max_results_per_item)
            
            if products:
                visual_results.append({
                    'category': crop['category'],
                    'description': crop['description'],
                    'crop_image': crop['path'],
                    'visual_matches': products
                })
        
        # Add to analysis
        analysis['visual_search_results'] = visual_results
        analysis['visual_search_metadata'] = {
            'total_crops_searched': len(crops_to_search),
            'successful_searches': len(visual_results),
            'total_matches_found': sum(len(r['visual_matches']) for r in visual_results),
            'provider': self.provider
        }
        
        # Save
        if not output_file:
            input_path = Path(analysis_file)
            output_file = input_path.parent / f"{input_path.stem}_with_visual_search.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        total_matches = sum(len(r['visual_matches']) for r in visual_results)
        logger.info("visual search complete", extra={
            "step": "enrich",
            "count": total_matches,
            "detail": f"searched={len(crops_to_search)}, matches={total_matches}, saved={output_file}"
        })
        
        return analysis
    
    def print_visual_search_summary(self, analysis_file: str):
        """Print summary of visual search results."""
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        results = analysis.get('visual_search_results', [])
        
        if not results:
            logger.info("no visual search results found", extra={"step": "visual_summary"})
            return
        
        logger.info("visual search results summary", extra={"step": "visual_summary", "count": len(results)})
        
        for item in results:
            logger.info("visual result", extra={
                "step": "visual_summary",
                "detail": f"{item['category'].upper()}: {item['description']}, crop={Path(item['crop_image']).name}, matches={len(item['visual_matches'])}"
            })
            
            for i, match in enumerate(item['visual_matches'][:5], 1):
                logger.debug("match", extra={
                    "step": "visual_summary",
                    "detail": f"{match['title'][:60]}, price={match.get('price', 'N/A')}, source={match.get('source', 'N/A')}"
                })


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Visual Search - Find products using actual images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visual search with SerpAPI (India by default)
  python3 visual_search.py final-output/image_complete_analysis.json

  # Search with specific location
  python3 visual_search.py analysis.json --location "Mumbai, India"
  python3 visual_search.py analysis.json --location "Delhi, India"

  # Search for US market
  python3 visual_search.py analysis.json --location "New York, USA" --country us

  # Specify output file
  python3 visual_search.py analysis.json -o visual_results.json

  # Limit results per image
  python3 visual_search.py analysis.json --max-results 5

  # Show summary only
  python3 visual_search.py analysis_with_visual_search.json --summary

Setup:
  1. Get SerpAPI key: https://serpapi.com/users/sign_up (100 free searches/month)
  2. Add to .env: SERPAPI_KEY=your_key_here
  3. Run visual search!

Note: Visual search is more accurate than text search for fashion/products.
        """
    )
    parser.add_argument("analysis_file", help="Path to analysis JSON (with crop images)")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--max-results", type=int, default=10,
                       help="Max results per image (default: 10)")
    parser.add_argument("--provider", default="serpapi",
                       choices=["serpapi", "google-lens", "bing-visual"],
                       help="Visual search provider (default: serpapi)")
    parser.add_argument("--location", default="India",
                       help="Location for search results (default: India)")
    parser.add_argument("--country", default="in",
                       help="Country code for results (default: in for India)")
    parser.add_argument("--summary", action="store_true",
                       help="Show summary (for already enriched files)")
    
    args = parser.parse_args()
    
    try:
        searcher = VisualSearcher(
            args.provider,
            location=args.location,
            country=args.country
        )
        
        if args.summary:
            searcher.print_visual_search_summary(args.analysis_file)
        else:
            searcher.enrich_with_visual_search(
                args.analysis_file,
                args.output,
                args.max_results
            )
            
            # Show summary
            output_file = args.output or str(
                Path(args.analysis_file).parent / 
                f"{Path(args.analysis_file).stem}_with_visual_search.json"
            )
            searcher.print_visual_search_summary(output_file)
    
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
