#!/usr/bin/env python3
"""
Amazon Shopping Integration
Scrapes Amazon for products based on analysis JSON.
Searches for clothing, furniture, products, electronics, etc.
"""

import json
import os
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from pathlib import Path
import time
import random
from urllib.parse import quote

from logging_config import get_logger
logger = get_logger("amazon")


class AmazonShopper:
    """Scrapes Amazon for products based on image analysis."""
    
    def __init__(self, region: str = "com"):
        """
        Initialize Amazon shopper.
        
        Args:
            region: Amazon region (com, in, co.uk, de, etc.)
        """
        self.region = region
        self.base_url = f"https://www.amazon.{region}"
        
        # Realistic headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _is_valid_brand(self, brand: str) -> bool:
        """Check if brand name is valid (not a placeholder or negative)."""
        if not brand:
            return False
        
        brand_lower = brand.lower().strip()
        
        # Invalid brand indicators
        invalid_keywords = [
            'unknown', 'not visible', 'not found', 'unclear', 'none',
            'no brand', 'not identifiable', 'cannot determine', 'n/a',
            'not specified', 'generic', 'unbranded', 'no logo',
            'not readable', 'obscured', 'hidden', 'not clear'
        ]
        
        # Check if brand contains any invalid keywords
        for keyword in invalid_keywords:
            if keyword in brand_lower:
                return False
        
        # Brand should have at least 2 characters
        if len(brand_lower) < 2:
            return False
        
        return True
    
    def build_search_query(self, item_data: Dict, category: str) -> str:
        """Build smart search query from item data."""
        query_parts = []
        
        if category == "clothing":
            # For clothing: gender + description + colors + style
            gender = item_data.get('gender', '')
            clothing = item_data.get('clothing', {})
            
            # Add gender
            if gender and gender not in ['unknown', 'unclear']:
                query_parts.append(gender)
            
            # Add clothing description (main item)
            description = clothing.get('description', '')
            if description:
                # Clean description - take first 5 words max
                desc_words = description.split()[:5]
                query_parts.extend(desc_words)
            
            # Add colors (max 2 primary colors)
            colors = clothing.get('colors', [])
            if colors and isinstance(colors, list):
                valid_colors = [c for c in colors[:2] if c not in ['unknown', 'unclear', 'mixed']]
                query_parts.extend(valid_colors)
            
            # Add style
            style = clothing.get('style', '')
            if style and style not in ['unknown', 'unclear', 'standard']:
                query_parts.append(style)
        
        elif category == "product":
            # For products: brand + type + material + colors
            brand = item_data.get('brand')
            product_type = item_data.get('product_type', '')
            material = item_data.get('material', '')
            colors = item_data.get('color', [])
            size = item_data.get('size', '')
            
            # Only add brand if it's valid (not "unknown", "not visible", etc.)
            if brand and self._is_valid_brand(brand):
                query_parts.append(brand)
            
            # Add product type
            if product_type and product_type != 'unknown':
                query_parts.append(product_type)
            
            # Add material if meaningful
            if material and material not in ['unknown', 'unclear', 'not visible']:
                query_parts.append(material)
            
            # Add primary color
            if colors and isinstance(colors, list) and len(colors) > 0:
                primary_color = colors[0]
                if primary_color not in ['unknown', 'unclear', 'mixed']:
                    query_parts.append(primary_color)
            
            # Add size if specific
            if size and size not in ['unknown', 'unclear', 'medium', 'standard']:
                query_parts.append(size)
        
        elif category == "electronics":
            # For electronics: brand + model + type + color
            brand = item_data.get('brand')
            model = item_data.get('model')
            item_type = item_data.get('type', '')
            color = item_data.get('color', '')
            
            # Only add brand if valid
            if brand and self._is_valid_brand(brand):
                query_parts.append(brand)
            
            # Add model if available
            if model and model not in ['unknown', 'unclear', 'not visible']:
                query_parts.append(model)
            
            # Add type
            if item_type and item_type != 'unknown':
                query_parts.append(item_type)
            
            # Add color if meaningful
            if color and color not in ['unknown', 'unclear', 'black', 'white']:
                query_parts.append(color)
        
        elif category == "furniture":
            # For furniture: type + material + style + colors
            item_type = item_data.get('type', '')
            material = item_data.get('material', '')
            style = item_data.get('style', '')
            colors = item_data.get('color', [])
            
            # Add type
            if item_type and item_type != 'unknown':
                query_parts.append(item_type)
            
            # Add material
            if material and material not in ['unknown', 'unclear', 'mixed']:
                query_parts.append(material)
            
            # Add primary color
            if colors and isinstance(colors, list) and len(colors) > 0:
                primary_color = colors[0]
                if primary_color not in ['unknown', 'unclear', 'mixed']:
                    query_parts.append(primary_color)
            
            # Add style
            if style and style not in ['unknown', 'unclear', 'standard']:
                query_parts.append(style)
        
        elif category == "accessory":
            # For accessories from clothing
            gender = item_data.get('gender', '')
            item = item_data.get('item', '')
            
            if gender and gender != 'unknown':
                query_parts.append(gender)
            query_parts.append(item)
        
        elif category == "held_item":
            # For items person is holding
            gender = item_data.get('gender', '')
            item = item_data.get('item', '')
            description = item_data.get('description', '')
            
            if gender and gender != 'unknown':
                query_parts.append(gender)
            if item:
                query_parts.append(item)
            elif description:
                query_parts.append(description)
        
        elif category == "pet_product":
            # For pet supplies
            query_parts.append(item_data.get('item', ''))
        
        elif category == "vehicle_accessory":
            # For vehicle accessories
            make = item_data.get('make', '')
            model = item_data.get('model', '')
            
            if make:
                query_parts.append(make)
            if model:
                query_parts.append(model)
            query_parts.append('accessories')
        
        elif category == "other":
            # For other objects: brand + type + material + colors
            obj_type = item_data.get('type', '')
            brand = item_data.get('brand')
            material = item_data.get('material', '')
            colors = item_data.get('color', [])
            
            # Only add brand if valid
            if brand and self._is_valid_brand(brand):
                query_parts.append(brand)
            
            # Add type
            if obj_type and obj_type != 'unknown':
                query_parts.append(obj_type)
            
            # Add material
            if material and material not in ['unknown', 'unclear', 'mixed']:
                query_parts.append(material)
            
            # Add primary color
            if colors and isinstance(colors, list) and len(colors) > 0:
                primary_color = colors[0]
                if primary_color not in ['unknown', 'unclear', 'mixed']:
                    query_parts.append(primary_color)
        
        # Clean and join
        query = ' '.join(str(p) for p in query_parts if p)
        return query.strip()
    
    def search_amazon(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for products via SerpAPI Google Shopping.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
        
        Returns:
            List of product dictionaries
        """
        if not query:
            return []
        
        logger.info("searching", extra={"step": "search_amazon", "detail": query})
        
        serpapi_key = os.getenv('SERPAPI_KEY')
        if not serpapi_key:
            logger.warning("SERPAPI_KEY not set, skipping search", extra={"step": "search_amazon"})
            return []
        
        try:
            params = {
                'engine': 'google_shopping',
                'q': query,
                'api_key': serpapi_key,
                'num': max_results,
                'gl': 'in' if self.region == 'in' else 'us',
            }
            
            response = requests.get('https://serpapi.com/search', params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            products = []
            for item in data.get('shopping_results', [])[:max_results]:
                products.append({
                    'title': item.get('title', ''),
                    'price': item.get('extracted_price') or item.get('price', ''),
                    'url': item.get('link', ''),
                    'image': item.get('thumbnail', ''),
                    'rating': item.get('rating'),
                    'reviews': item.get('reviews'),
                    'source': item.get('source', 'Google Shopping'),
                })
            
            logger.info("search complete", extra={"step": "search_amazon", "count": len(products), "detail": query})
            return products
        
        except Exception as e:
            logger.warning("search failed", extra={"step": "search_amazon", "error": str(e), "detail": query})
            return []
    
    def _parse_product(self, item) -> Optional[Dict]:
        """Parse product information from search result item."""
        try:
            # Title
            title_elem = item.find('h2')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                return None
            
            # URL
            link_elem = item.find('a', {'class': 'a-link-normal s-no-outline'})
            url = f"{self.base_url}{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else None
            
            # Price
            price_elem = item.find('span', {'class': 'a-price-whole'})
            price = price_elem.get_text(strip=True) if price_elem else None
            
            # Rating
            rating_elem = item.find('span', {'class': 'a-icon-alt'})
            rating = rating_elem.get_text(strip=True) if rating_elem else None
            
            # Image
            img_elem = item.find('img', {'class': 's-image'})
            image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
            
            # Reviews count
            reviews_elem = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = reviews_elem.get_text(strip=True) if reviews_elem else None
            
            return {
                'title': title,
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'url': url,
                'image': image,
                'source': f'Amazon.{self.region}'
            }
        
        except Exception as e:
            return None
    
    def extract_searchable_items(self, analysis: Dict) -> List[Dict]:
        """Extract all searchable items from analysis JSON."""
        searchable_items = []
        
        # 1. People's clothing and accessories
        for idx, person in enumerate(analysis.get('people', []), 1):
            clothing = person.get('clothing', {})
            
            # Main outfit
            if clothing.get('description'):
                searchable_items.append({
                    'category': 'clothing',
                    'type': 'outfit',
                    'data': person,
                    'priority': 1,
                    'source': f'person_{idx}'
                })
            
            # Individual accessories from accessories array
            accessories = clothing.get('accessories', [])
            for accessory in accessories:
                searchable_items.append({
                    'category': 'accessory',
                    'type': accessory,
                    'data': {'item': accessory, 'gender': person.get('gender')},
                    'priority': 2,
                    'source': f'person_{idx}_accessory'
                })
            
            # Held items (from schema: held_items array)
            held_items = person.get('held_items', [])
            for held_item in held_items:
                item_name = held_item.get('item', '')
                if item_name:
                    searchable_items.append({
                        'category': 'held_item',
                        'type': item_name,
                        'data': {
                            'item': item_name,
                            'description': held_item.get('description', ''),
                            'gender': person.get('gender')
                        },
                        'priority': 1,
                        'source': f'person_{idx}_held'
                    })
        
        # 2. Products (bottles, cups, etc.) - from schema
        for idx, product in enumerate(analysis.get('products', []), 1):
            # Check if we have brand or product_type
            brand = product.get('brand')
            product_type = product.get('product_type', '')
            
            if brand or product_type:
                searchable_items.append({
                    'category': 'product',
                    'type': product_type or 'product',
                    'data': product,
                    'priority': 1,
                    'source': f'product_{idx}'
                })
        
        # 3. Electronics - from schema
        for idx, electronic in enumerate(analysis.get('electronics', []), 1):
            brand = electronic.get('brand')
            model = electronic.get('model')
            elec_type = electronic.get('type', '')
            
            if brand or model or elec_type:
                searchable_items.append({
                    'category': 'electronics',
                    'type': elec_type or 'electronic',
                    'data': electronic,
                    'priority': 1,
                    'source': f'electronics_{idx}'
                })
        
        # 4. Furniture - from schema
        for idx, furniture in enumerate(analysis.get('furniture', []), 1):
            furn_type = furniture.get('type', '')
            material = furniture.get('material', '')
            style = furniture.get('style', '')
            
            if furn_type:
                searchable_items.append({
                    'category': 'furniture',
                    'type': furn_type,
                    'data': furniture,
                    'priority': 2,
                    'source': f'furniture_{idx}'
                })
        
        # 5. Animals (pet products) - from schema
        for idx, animal in enumerate(analysis.get('animals', []), 1):
            breed = animal.get('breed', '')
            size = animal.get('size', '')
            
            if breed and breed != 'unknown':
                # Search for pet products
                searchable_items.append({
                    'category': 'pet_product',
                    'type': f'{breed} pet supplies',
                    'data': {
                        'breed': breed,
                        'size': size,
                        'item': f'{breed} dog supplies' if 'dog' in breed.lower() else f'{breed} cat supplies'
                    },
                    'priority': 3,
                    'source': f'animal_{idx}'
                })
        
        # 6. Vehicles (accessories/parts) - from schema
        for idx, vehicle in enumerate(analysis.get('vehicles', []), 1):
            make = vehicle.get('make')
            model = vehicle.get('model')
            body_type = vehicle.get('body_type', '')
            
            if make or model:
                # Search for vehicle accessories
                searchable_items.append({
                    'category': 'vehicle_accessory',
                    'type': f'{make} {model} accessories' if make and model else 'car accessories',
                    'data': vehicle,
                    'priority': 3,
                    'source': f'vehicle_{idx}'
                })
        
        # 7. Other objects - from schema
        for idx, obj in enumerate(analysis.get('other_objects', []), 1):
            obj_type = obj.get('type', '')
            brand = obj.get('brand')
            
            if obj_type:
                searchable_items.append({
                    'category': 'other',
                    'type': obj_type,
                    'data': obj,
                    'priority': 3,
                    'source': f'other_{idx}'
                })
        
        # Sort by priority (lower number = higher priority)
        searchable_items.sort(key=lambda x: x['priority'])
        
        return searchable_items
    
    def enrich_with_shopping(self, analysis_file: str, output_file: str = None,
                            max_products_per_item: int = 5) -> Dict:
        """
        Enrich analysis with Amazon shopping results.
        
        Args:
            analysis_file: Path to enriched analysis JSON
            output_file: Path to save shopping-enriched JSON
            max_products_per_item: Max products to fetch per item
        
        Returns:
            Shopping-enriched analysis
        """
        logger.info("amazon shopping started", extra={"step": "enrich_with_shopping", "detail": analysis_file})
        
        # Load analysis
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        logger.info("analysis loaded", extra={"step": "enrich_with_shopping", "detail": analysis_file})
        
        # Extract searchable items
        searchable_items = self.extract_searchable_items(analysis)
        
        if not searchable_items:
            logger.warning("no searchable items found in analysis", extra={"step": "enrich_with_shopping"})
            return analysis
        
        logger.info("searchable items found", extra={"step": "enrich_with_shopping", "count": len(searchable_items)})
        
        # Search Amazon for each item
        shopping_results = []
        
        for i, item in enumerate(searchable_items, 1):
            logger.info("processing item", extra={"step": "enrich_with_shopping", "detail": f"{item['category']}: {item['type']} ({i}/{len(searchable_items)})"})
            
            # Build search query
            query = self.build_search_query(item['data'], item['category'])
            
            if not query:
                logger.warning("could not build query, skipping", extra={"step": "enrich_with_shopping", "detail": item['type']})
                continue
            
            # Search Amazon
            products = self.search_amazon(query, max_products_per_item)
            
            if products:
                shopping_results.append({
                    'category': item['category'],
                    'type': item['type'],
                    'search_query': query,
                    'products': products
                })
        
        # Add shopping results to analysis
        analysis['shopping_recommendations'] = shopping_results
        analysis['shopping_metadata'] = {
            'total_searches': len(searchable_items),
            'successful_searches': len(shopping_results),
            'total_products_found': sum(len(r['products']) for r in shopping_results),
            'amazon_region': self.region
        }
        
        # Save enriched analysis
        if not output_file:
            input_path = Path(analysis_file)
            output_file = input_path.parent / f"{input_path.stem}_with_shopping.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        total_products = sum(len(r['products']) for r in shopping_results)
        logger.info("amazon shopping complete", extra={
            "step": "enrich_with_shopping",
            "count": total_products,
            "detail": f"searched={len(searchable_items)}, found={total_products}, saved={output_file}"
        })
        
        return analysis
    
    def print_shopping_summary(self, analysis_file: str):
        """Print a summary of shopping recommendations."""
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        shopping = analysis.get('shopping_recommendations', [])
        
        if not shopping:
            logger.info("no shopping recommendations found", extra={"step": "shopping_summary"})
            return
        
        logger.info("shopping recommendations summary", extra={"step": "shopping_summary", "count": len(shopping)})
        
        for item in shopping:
            logger.info("recommendation", extra={
                "step": "shopping_summary",
                "detail": f"{item['category'].upper()}: {item['type']}, query={item['search_query']}, products={len(item['products'])}"
            })
            
            for i, product in enumerate(item['products'][:3], 1):
                logger.debug("product", extra={
                    "step": "shopping_summary",
                    "detail": f"{product['title'][:60]}, price={product.get('price', 'N/A')}, rating={product.get('rating', 'N/A')}"
                })


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Amazon Shopping Integration - Find products from image analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add shopping recommendations to analysis
  python3 amazon_shopping.py final-output/image_complete_analysis_enriched.json

  # Specify output file
  python3 amazon_shopping.py analysis.json -o shopping_results.json

  # Limit products per item
  python3 amazon_shopping.py analysis.json --max-products 3

  # Use Amazon India
  python3 amazon_shopping.py analysis.json --region in

  # Show summary only
  python3 amazon_shopping.py analysis_with_shopping.json --summary

Note: Web scraping may be against Amazon's TOS. Use responsibly and consider official APIs.
        """
    )
    parser.add_argument("analysis_file", help="Path to enriched analysis JSON")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--max-products", type=int, default=5,
                       help="Max products per item (default: 5)")
    parser.add_argument("--region", default="com",
                       help="Amazon region: com, in, co.uk, de, etc. (default: com)")
    parser.add_argument("--summary", action="store_true",
                       help="Show shopping summary (for already enriched files)")
    
    args = parser.parse_args()
    
    try:
        shopper = AmazonShopper(args.region)
        
        if args.summary:
            # Just show summary
            shopper.print_shopping_summary(args.analysis_file)
        else:
            # Enrich and save
            shopper.enrich_with_shopping(
                args.analysis_file,
                args.output,
                args.max_products
            )
            
            # Show summary
            output_file = args.output or str(
                Path(args.analysis_file).parent / 
                f"{Path(args.analysis_file).stem}_with_shopping.json"
            )
            shopper.print_shopping_summary(output_file)
    
    except FileNotFoundError:
        logger.error("file not found", extra={"error": args.analysis_file, "step": "main"})
        exit(1)
    except Exception as e:
        logger.error("unexpected error", extra={"error": str(e), "step": "main"})
        exit(1)


if __name__ == "__main__":
    main()
