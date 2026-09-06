#!/usr/bin/env python3
"""
Unified Shopping Pipeline
Combines Amazon text search (for clothing) + Visual search (for objects).
Uses the best search method for each category.
"""

import json
from pathlib import Path
from typing import Dict
import sys

# Import our existing modules
from .amazon_shopping import AmazonShopper
from .visual_search import VisualSearcher

from logging_config import get_logger
logger = get_logger("shopping")


class UnifiedShopper:
    """Unified shopping using both text and visual search."""
    
    def __init__(self, amazon_region: str = "in", visual_provider: str = "serpapi"):
        """
        Initialize unified shopper.
        
        Args:
            amazon_region: Amazon region (com, in, co.uk, etc.)
            visual_provider: Visual search provider (serpapi, bing-visual)
        """
        logger.info("initializing unified shopping pipeline", extra={
            "step": "init",
            "detail": f"amazon_region={amazon_region}, visual_provider={visual_provider}"
        })
        
        self.amazon = AmazonShopper(amazon_region)
        self.visual = VisualSearcher(visual_provider)
    
    def enrich_with_unified_shopping(self, analysis_file: str, output_file: str = None,
                                     max_products_per_item: int = 5,
                                     max_visual_results: int = 10) -> Dict:
        """
        Enrich analysis with both text and visual shopping.
        
        Strategy:
        - Text search (Amazon): People's clothing, accessories, held items
        - Visual search (SerpAPI): Products, electronics, furniture, other objects
        
        Args:
            analysis_file: Path to analysis JSON
            output_file: Output path
            max_products_per_item: Max products per text search
            max_visual_results: Max results per visual search
        
        Returns:
            Enriched analysis with shopping results
        """
        logger.info("unified shopping pipeline started", extra={"step": "unified_enrich", "detail": analysis_file})
        
        # Load analysis
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        logger.info("analysis loaded", extra={"step": "unified_enrich", "detail": analysis_file})
        
        # ============================================================
        # PART 1: TEXT SEARCH (Amazon) for Clothing
        # ============================================================
        logger.info("text search phase started (amazon) — best for clothing, accessories, style descriptions", extra={"step": "text_search"})
        
        text_searchable = self._extract_text_searchable_items(analysis)
        
        if text_searchable:
            logger.info("text-searchable items found", extra={"step": "text_search", "count": len(text_searchable)})
            
            text_results = []
            for i, item in enumerate(text_searchable, 1):
                logger.info("text search item", extra={"step": "text_search", "detail": f"{item['category']}: {item['type']} ({i}/{len(text_searchable)})"})
                
                # Build query
                query = self.amazon.build_search_query(item['data'], item['category'])
                
                if query:
                    # Search Amazon
                    products = self.amazon.search_amazon(query, max_products_per_item)
                    
                    if products:
                        text_results.append({
                            'category': item['category'],
                            'type': item['type'],
                            'search_query': query,
                            'search_method': 'text',
                            'products': products
                        })
            
            logger.info("text search phase complete", extra={"step": "text_search", "count": len(text_results)})
        else:
            logger.info("no items for text search", extra={"step": "text_search"})
            text_results = []
        
        # ============================================================
        # PART 2: VISUAL SEARCH (SerpAPI) for Objects
        # ============================================================
        logger.info("visual search phase started (serpapi + google lens) — best for products, electronics, furniture", extra={"step": "visual_search"})
        
        visual_searchable = self._extract_visual_searchable_items(analysis)
        
        if visual_searchable:
            logger.info("visual-searchable items found", extra={"step": "visual_search", "count": len(visual_searchable)})
            
            visual_results = []
            for i, item in enumerate(visual_searchable, 1):
                logger.info("visual search item", extra={"step": "visual_search", "detail": f"{item['category']}: {item['description']} ({i}/{len(visual_searchable)})"})
                
                # Visual search by image
                products = self.visual.search_by_image(item['path'], max_visual_results)
                
                if products:
                    visual_results.append({
                        'category': item['category'],
                        'type': item['description'],
                        'crop_image': item['path'],
                        'search_method': 'visual',
                        'products': products
                    })
            
            logger.info("visual search phase complete", extra={"step": "visual_search", "count": len(visual_results)})
        else:
            logger.info("no items for visual search", extra={"step": "visual_search"})
            visual_results = []
        
        # ============================================================
        # COMBINE RESULTS
        # ============================================================
        all_results = text_results + visual_results
        
        # Add to analysis
        analysis['unified_shopping_results'] = all_results
        analysis['unified_shopping_metadata'] = {
            'total_searches': len(text_searchable) + len(visual_searchable),
            'text_searches': len(text_results),
            'visual_searches': len(visual_results),
            'total_products_found': sum(len(r['products']) for r in all_results),
            'amazon_region': self.amazon.region,
            'visual_provider': self.visual.provider
        }
        
        # Save
        if not output_file:
            input_path = Path(analysis_file)
            output_file = input_path.parent / f"{input_path.stem}_with_unified_shopping.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        total_products = sum(len(r['products']) for r in all_results)
        logger.info("unified shopping complete", extra={
            "step": "unified_enrich",
            "count": total_products,
            "detail": f"text={len(text_results)}, visual={len(visual_results)}, total_products={total_products}, saved={output_file}"
        })
        
        return analysis
    
    def _extract_text_searchable_items(self, analysis: Dict) -> list:
        """Extract items best suited for text search (clothing)."""
        items = []
        
        # People's clothing and accessories (text search works better)
        for idx, person in enumerate(analysis.get('people', []), 1):
            clothing = person.get('clothing', {})
            if isinstance(clothing, str):
                clothing = {'description': clothing, 'colors': [], 'style': '', 'accessories': []}
            
            # Main outfit
            if clothing.get('description'):
                items.append({
                    'category': 'clothing',
                    'type': 'outfit',
                    'data': person,
                    'source': f'person_{idx}'
                })
            
            # Accessories from clothing
            accessories = clothing.get('accessories', [])
            for accessory in accessories:
                items.append({
                    'category': 'accessory',
                    'type': accessory,
                    'data': {'item': accessory, 'gender': person.get('gender')},
                    'source': f'person_{idx}_accessory'
                })
            
            # Held items
            held_items = person.get('held_items', [])
            for held_item in held_items:
                item_name = held_item.get('item', '')
                if item_name:
                    items.append({
                        'category': 'held_item',
                        'type': item_name,
                        'data': {
                            'item': item_name,
                            'description': held_item.get('description', ''),
                            'gender': person.get('gender')
                        },
                        'source': f'person_{idx}_held'
                    })
        
        return items
    
    def _extract_visual_searchable_items(self, analysis: Dict) -> list:
        """Extract items best suited for visual search (objects with crop images)."""
        items = []
        
        def is_valid_image(crop_path):
            """Check if crop image is valid (URL or existing file)."""
            if not crop_path:
                return False
            # Check if it's a URL
            if crop_path.startswith('http://') or crop_path.startswith('https://'):
                return True
            # Check if it's a local file that exists
            return Path(crop_path).exists()
        
        # Products (bottles, cups, etc.)
        for idx, product in enumerate(analysis.get('products', []), 1):
            crop_path = product.get('crop_image')
            if is_valid_image(crop_path):
                brand = product.get('brand', '')
                product_type = product.get('product_type', 'product')
                colors = product.get('color', [])
                
                desc_parts = []
                if brand and brand not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(brand)
                desc_parts.append(product_type)
                if colors and isinstance(colors, list) and len(colors) > 0:
                    desc_parts.append(colors[0])
                
                items.append({
                    'path': crop_path,
                    'category': 'product',
                    'description': ' '.join(desc_parts),
                    'data': product
                })
        
        # Electronics
        for idx, electronic in enumerate(analysis.get('electronics', []), 1):
            crop_path = electronic.get('crop_image')
            if is_valid_image(crop_path):
                brand = electronic.get('brand', '')
                model = electronic.get('model', '')
                elec_type = electronic.get('type', 'electronic')
                
                desc_parts = []
                if brand and brand not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(brand)
                if model and model not in ['unknown', 'not visible', 'unclear']:
                    desc_parts.append(model)
                desc_parts.append(elec_type)
                
                items.append({
                    'path': crop_path,
                    'category': 'electronics',
                    'description': ' '.join(desc_parts),
                    'data': electronic
                })
        
        # Furniture
        for idx, furniture in enumerate(analysis.get('furniture', []), 1):
            crop_path = furniture.get('crop_image')
            if is_valid_image(crop_path):
                furn_type = furniture.get('type', 'furniture')
                material = furniture.get('material', '')
                style = furniture.get('style', '')
                
                desc_parts = [furn_type]
                if material and material not in ['unknown', 'unclear']:
                    desc_parts.append(material)
                if style and style not in ['unknown', 'unclear']:
                    desc_parts.append(style)
                
                items.append({
                    'path': crop_path,
                    'category': 'furniture',
                    'description': ' '.join(desc_parts),
                    'data': furniture
                })
        
        # Other objects (ties, accessories, etc.)
        for idx, obj in enumerate(analysis.get('other_objects', []), 1):
            crop_path = obj.get('crop_image')
            if is_valid_image(crop_path):
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
                
                items.append({
                    'path': crop_path,
                    'category': 'other_object',
                    'description': ' '.join(desc_parts),
                    'data': obj
                })
        
        return items
    
    def print_summary(self, analysis_file: str):
        """Print summary of unified shopping results."""
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        results = analysis.get('unified_shopping_results', [])
        
        if not results:
            logger.info("no shopping results found", extra={"step": "unified_summary"})
            return
        
        logger.info("unified shopping results summary", extra={"step": "unified_summary", "count": len(results)})
        
        # Group by search method
        text_results = [r for r in results if r.get('search_method') == 'text']
        visual_results = [r for r in results if r.get('search_method') == 'visual']
        
        if text_results:
            logger.info("text search results (amazon)", extra={"step": "unified_summary", "count": len(text_results)})
            for item in text_results:
                logger.info("text result", extra={
                    "step": "unified_summary",
                    "detail": f"{item['category'].upper()}: {item['type']}, query={item.get('search_query', 'N/A')}, products={len(item['products'])}"
                })
                
                for i, product in enumerate(item['products'][:3], 1):
                    logger.debug("product", extra={
                        "step": "unified_summary",
                        "detail": f"{product['title'][:60]}, price={product.get('price', 'N/A')}, rating={product.get('rating', 'N/A')}"
                    })
        
        if visual_results:
            logger.info("visual search results (serpapi)", extra={"step": "unified_summary", "count": len(visual_results)})
            for item in visual_results:
                logger.info("visual result", extra={
                    "step": "unified_summary",
                    "detail": f"{item['category'].upper()}: {item['type']}, crop={Path(item.get('crop_image', '')).name}, products={len(item['products'])}"
                })
                
                for i, product in enumerate(item['products'][:3], 1):
                    logger.debug("product", extra={
                        "step": "unified_summary",
                        "detail": f"{product['title'][:60]}, price={product.get('price', 'N/A')}, source={product.get('source', 'N/A')}"
                    })


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Unified Shopping - Best of both text and visual search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run unified shopping (text + visual)
  python3 unified_shopping.py final-output/image_complete_analysis.json

  # Specify output file
  python3 unified_shopping.py analysis.json -o shopping_results.json

  # Limit results
  python3 unified_shopping.py analysis.json --max-text 3 --max-visual 5

  # Use Amazon India
  python3 unified_shopping.py analysis.json --amazon-region in

  # Show summary only
  python3 unified_shopping.py analysis_with_unified_shopping.json --summary

How it works:
  🔤 Text Search (Amazon):
     - People's clothing (style, color, description)
     - Accessories (watches, sunglasses, etc.)
     - Held items (bags, phones, etc.)
  
  👁️  Visual Search (SerpAPI):
     - Products (bottles, cups, exact visual match)
     - Electronics (phones, laptops, exact model)
     - Furniture (chairs, tables, similar style)
     - Other objects (ties, accessories, exact match)

Setup:
  1. Amazon: No API key needed (web scraping)
  2. SerpAPI: Get key at https://serpapi.com/users/sign_up
  3. ImgBB: Get key at https://api.imgbb.com/
  4. Add to .env:
     SERPAPI_KEY=your_key
     IMGBB_API_KEY=your_key
        """
    )
    parser.add_argument("analysis_file", help="Path to analysis JSON")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--max-text", type=int, default=5,
                       help="Max products per text search (default: 5)")
    parser.add_argument("--max-visual", type=int, default=10,
                       help="Max products per visual search (default: 10)")
    parser.add_argument("--amazon-region", default="com",
                       help="Amazon region: com, in, co.uk, etc. (default: com)")
    parser.add_argument("--visual-provider", default="serpapi",
                       choices=["serpapi", "bing-visual"],
                       help="Visual search provider (default: serpapi)")
    parser.add_argument("--summary", action="store_true",
                       help="Show summary (for already enriched files)")
    
    args = parser.parse_args()
    
    try:
        shopper = UnifiedShopper(args.amazon_region, args.visual_provider)
        
        if args.summary:
            shopper.print_summary(args.analysis_file)
        else:
            shopper.enrich_with_unified_shopping(
                args.analysis_file,
                args.output,
                args.max_text,
                args.max_visual
            )
            
            # Show summary
            output_file = args.output or str(
                Path(args.analysis_file).parent / 
                f"{Path(args.analysis_file).stem}_with_unified_shopping.json"
            )
            shopper.print_summary(output_file)
    
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
