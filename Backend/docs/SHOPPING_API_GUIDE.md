## Shopping Recommendations API

Complete guide for the `/api/shopping-recommendations` endpoint.

## Overview

The shopping recommendations endpoint takes analysis data from the `/analyze` endpoint and finds shopping recommendations for:
- **Clothing** (text search via Amazon)
- **Accessories** (text search via Amazon)
- **Products** (visual search via Google Lens/SerpAPI)
- **Electronics** (visual search via Google Lens/SerpAPI)
- **Furniture** (visual search via Google Lens/SerpAPI)

## Endpoint

```
POST /api/shopping-recommendations
```

## Complete Workflow

### Step 1: Analyze Image

First, analyze an image to get clothing and product data:

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "movie_name": "Pathaan",
    "enable_vision": 1
  }'
```

### Step 2: Get Shopping Recommendations

Use the analysis data to get shopping recommendations:

```bash
curl -X POST "http://localhost:8000/api/shopping-recommendations" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_data": { ... analysis from step 1 ... },
    "max_products_per_item": 5,
    "max_visual_results": 10,
    "amazon_region": "com"
  }'
```

## Request

### Request Body

```json
{
  "analysis_data": {
    "people": [
      {
        "name": "Shah Rukh Khan",
        "clothing": {
          "description": "Black leather jacket with white shirt",
          "colors": ["black", "white"],
          "style": "casual",
          "accessories": ["sunglasses", "watch"]
        },
        "held_items": [
          {
            "item": "phone",
            "description": "smartphone"
          }
        ],
        "gender": "male"
      }
    ],
    "products": [
      {
        "brand": "Coca Cola",
        "product_type": "bottle",
        "color": ["red"],
        "crop_image": "output/product_1.png"
      }
    ],
    "electronics": [],
    "furniture": []
  },
  "max_products_per_item": 5,
  "max_visual_results": 10,
  "amazon_region": "com"
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `analysis_data` | object | ✓ | - | Analysis JSON from /analyze endpoint |
| `max_products_per_item` | integer | | 5 | Max products per text search (1-20) |
| `max_visual_results` | integer | | 10 | Max results per visual search (1-30) |
| `amazon_region` | string | | "com" | Amazon region (com, in, co.uk, etc.) |

## Response

### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Found 45 products across 8 searches",
  "data": {
    "shopping_results": [
      {
        "category": "clothing",
        "type": "outfit",
        "search_query": "men's black leather jacket casual",
        "search_method": "text",
        "products": [
          {
            "title": "Men's Genuine Leather Jacket Black Slim Fit",
            "price": "$89.99",
            "rating": "4.5",
            "link": "https://amazon.com/...",
            "image": "https://..."
          }
        ]
      },
      {
        "category": "accessory",
        "type": "sunglasses",
        "search_query": "men's sunglasses",
        "search_method": "text",
        "products": [...]
      },
      {
        "category": "product",
        "type": "Coca Cola bottle",
        "crop_image": "output/product_1.png",
        "search_method": "visual",
        "products": [
          {
            "title": "Coca-Cola Classic 12 Pack",
            "price": "$5.99",
            "source": "Walmart",
            "link": "https://...",
            "thumbnail": "https://..."
          }
        ]
      }
    ],
    "metadata": {
      "total_searches": 8,
      "text_searches": 5,
      "visual_searches": 3,
      "total_products_found": 45,
      "amazon_region": "com",
      "visual_provider": "serpapi"
    },
    "summary": {
      "total_searches": 8,
      "text_searches": 5,
      "visual_searches": 3,
      "total_products_found": 45
    }
  }
}
```

## Search Methods

### Text Search (Amazon)

Used for:
- Clothing descriptions
- Accessories
- Held items

**Example:**
```json
{
  "category": "clothing",
  "type": "outfit",
  "search_query": "men's black leather jacket casual",
  "search_method": "text",
  "products": [...]
}
```

### Visual Search (Google Lens via SerpAPI)

Used for:
- Products with crop images
- Electronics with crop images
- Furniture with crop images

**Example:**
```json
{
  "category": "product",
  "type": "Coca Cola bottle",
  "crop_image": "output/product_1.png",
  "search_method": "visual",
  "products": [...]
}
```

## Usage Examples

### Python - Complete Workflow

```python
import requests

# Step 1: Analyze image
analyze_response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "image_url": "https://example.com/image.jpg",
        "movie_name": "Pathaan",
        "enable_vision": 1
    }
)

analysis_data = analyze_response.json()["data"]

# Step 2: Get shopping recommendations
shopping_response = requests.post(
    "http://localhost:8000/api/shopping-recommendations",
    json={
        "analysis_data": analysis_data,
        "max_products_per_item": 5,
        "max_visual_results": 10,
        "amazon_region": "com"
    }
)

shopping_data = shopping_response.json()["data"]

# Display results
for item in shopping_data["shopping_results"]:
    print(f"\n{item['category'].upper()}: {item['type']}")
    print(f"Search method: {item['search_method']}")
    print(f"Products found: {len(item['products'])}")
    
    for product in item['products'][:3]:
        print(f"  • {product['title']}")
        if product.get('price'):
            print(f"    Price: {product['price']}")
```

### Using the Example Script

```bash
# Complete workflow (analyze + shopping)
python example_shopping_api.py

# Custom image and movie
python example_shopping_api.py \
  --image-url "https://example.com/image.jpg" \
  --movie "Pathaan"

# Use Amazon India
python example_shopping_api.py --amazon-region in

# Faster (without vision analysis)
python example_shopping_api.py --no-vision

# Save results
python example_shopping_api.py --save
```

## Amazon Regions

Supported Amazon regions:

| Region | Code | Example |
|--------|------|---------|
| United States | `com` | amazon.com |
| India | `in` | amazon.in |
| United Kingdom | `co.uk` | amazon.co.uk |
| Canada | `ca` | amazon.ca |
| Germany | `de` | amazon.de |
| France | `fr` | amazon.fr |
| Japan | `jp` | amazon.co.jp |
| Australia | `com.au` | amazon.com.au |

## Product Fields

### Text Search Products (Amazon)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Product title |
| `price` | string | Price (e.g., "$89.99") |
| `rating` | string | Rating (e.g., "4.5") |
| `link` | string | Product URL |
| `image` | string | Product image URL |

### Visual Search Products (SerpAPI)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Product title |
| `price` | string | Price (if available) |
| `source` | string | Retailer name |
| `link` | string | Product URL |
| `thumbnail` | string | Product image URL |

## Requirements

### API Keys

Set in `.env` file:

```bash
# Required for visual search
SERPAPI_KEY=your_serpapi_key

# Required for uploading crop images (visual search)
IMGBB_API_KEY=your_imgbb_key

# Optional: TMDB for actor identification
TMDB_API_KEY=your_tmdb_key
```

Get API keys:
- SerpAPI: https://serpapi.com/users/sign_up (100 free searches/month)
- ImgBB: https://api.imgbb.com/ (free, unlimited)
- TMDB: https://www.themoviedb.org/settings/api (free)

### Dependencies

```bash
pip install -r requirements_api.txt
```

## Performance

### Processing Time

| Scenario | Time |
|----------|------|
| Text search only (3-5 items) | 5-10s |
| Visual search only (2-3 items) | 10-20s |
| Mixed (5 text + 3 visual) | 15-30s |

### Rate Limits

- **Amazon**: No official API, web scraping (be respectful)
- **SerpAPI**: 100 searches/month (free tier)

## Error Handling

### Missing API Keys

```json
{
  "detail": "Internal server error: SERPAPI_KEY not set"
}
```

**Solution:** Set `SERPAPI_KEY` in `.env` file

### Invalid Analysis Data

```json
{
  "detail": "Internal server error: ..."
}
```

**Solution:** Ensure analysis_data is from `/analyze` endpoint

### No Results Found

```json
{
  "success": true,
  "message": "Found 0 products across 0 searches",
  "data": {
    "shopping_results": [],
    ...
  }
}
```

**Reason:** No clothing or products detected in analysis

## Use Cases

### 1. E-commerce Integration

Get shopping recommendations for products in images:

```python
# Analyze product image
analysis = analyze_image(product_image_url, "Product Catalog")

# Get shopping recommendations
shopping = get_shopping_recommendations(analysis)

# Display similar products
for item in shopping["shopping_results"]:
    for product in item["products"]:
        display_product(product)
```

### 2. Fashion Recommendations

Find similar clothing items:

```python
# Analyze fashion image
analysis = analyze_image(fashion_image_url, "Fashion Show", enable_vision=1)

# Get clothing recommendations
shopping = get_shopping_recommendations(analysis, amazon_region="com")

# Filter clothing only
clothing_items = [
    item for item in shopping["shopping_results"]
    if item["category"] == "clothing"
]
```

### 3. Product Discovery

Find products from movie scenes:

```python
# Analyze movie scene
analysis = analyze_image(movie_scene_url, "Pathaan", enable_vision=1)

# Get all product recommendations
shopping = get_shopping_recommendations(analysis)

# Group by category
products_by_category = {}
for item in shopping["shopping_results"]:
    category = item["category"]
    if category not in products_by_category:
        products_by_category[category] = []
    products_by_category[category].append(item)
```

## Testing

### Using Postman

1. Import `Agentic_Pipeline_API.postman_collection.json`
2. Use "Get Shopping Recommendations" request
3. Modify `analysis_data` with your own data

### Using Example Script

```bash
python example_shopping_api.py --save
```

### Manual Testing

```bash
# Step 1: Analyze
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/image.jpg", "movie_name": "Pathaan", "enable_vision": 1}' \
  > analysis.json

# Step 2: Extract data and get shopping
curl -X POST "http://localhost:8000/api/shopping-recommendations" \
  -H "Content-Type: application/json" \
  -d @shopping_request.json
```

## Troubleshooting

### No Products Found

**Possible reasons:**
1. No clothing or products detected in image
2. Vision analysis disabled (`enable_vision=0`)
3. Crop images not accessible

**Solution:** Enable vision analysis and ensure image has detectable items

### SerpAPI Quota Exceeded

```
Error: SerpAPI quota exceeded
```

**Solution:** 
- Wait for quota reset (monthly)
- Upgrade SerpAPI plan
- Reduce `max_visual_results`

### Slow Response

**Optimization:**
- Reduce `max_products_per_item` (default: 5)
- Reduce `max_visual_results` (default: 10)
- Use text search only (disable visual search)

## Related Endpoints

- `POST /analyze` - Analyze image (required first step)
- `POST /api/more-movies` - Get actor movies
- `GET /health` - Check API health

## Support

For issues:
1. Check API keys in `.env`
2. Verify analysis data format
3. Check API logs for detailed errors
4. Review SerpAPI quota: https://serpapi.com/dashboard
