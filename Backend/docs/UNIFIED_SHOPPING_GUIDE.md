# Unified Shopping Guide

## Overview

The unified shopping pipeline combines **text search** and **visual search** to get the best results for each category.

## Strategy

### 🔤 Text Search (Amazon)
**Best for:** Clothing, accessories, style descriptions

- People's outfits (color, style, description)
- Accessories (watches, sunglasses, jewelry)
- Held items (bags, phones in hand)

**Why?** Text descriptions work better for fashion because you can search by style, color, and fit.

### 👁️ Visual Search (SerpAPI + Google Lens)
**Best for:** Products, electronics, exact visual matches

- Products (bottles, cups, exact brand/model)
- Electronics (phones, laptops, exact model)
- Furniture (chairs, tables, similar style)
- Other objects (ties, accessories, exact match)

**Why?** Visual search finds exact matches or visually similar items, perfect for products.

## Setup

### 1. Amazon (Text Search)
No API key needed - uses web scraping

### 2. SerpAPI (Visual Search)
```bash
# Get free key at: https://serpapi.com/users/sign_up
# 100 free searches/month
SERPAPI_KEY=your_key_here
```

### 3. ImgBB (Image Hosting)
```bash
# Get free key at: https://api.imgbb.com/
# Unlimited uploads
IMGBB_API_KEY=your_key_here
```

### 4. Add to .env
```bash
nano .env

# Add these lines:
SERPAPI_KEY=your_serpapi_key
IMGBB_API_KEY=your_imgbb_key
```

## Usage

### Basic Usage

```bash
python3 unified_shopping.py final-output/image_complete_analysis.json
```

### Complete Workflow

```bash
# Step 1: Analyze image
python3 agentic_pipeline.py actor_photo.jpg

# Step 2: Enrich with TMDB (optional)
python3 tmdb_enrichment.py final-output/actor_photo_complete_analysis.json

# Step 3: Unified shopping (text + visual)
python3 unified_shopping.py final-output/actor_photo_complete_analysis_enriched.json
```

## Advanced Options

### Limit Results

```bash
# Limit text search to 3 products, visual to 5
python3 unified_shopping.py analysis.json --max-text 3 --max-visual 5
```

### Custom Output

```bash
python3 unified_shopping.py analysis.json -o shopping_results.json
```

### Amazon Region

```bash
# Use Amazon India
python3 unified_shopping.py analysis.json --amazon-region in

# Use Amazon UK
python3 unified_shopping.py analysis.json --amazon-region co.uk
```

### View Summary Only

```bash
python3 unified_shopping.py analysis_with_unified_shopping.json --summary
```

## Output Structure

```json
{
  "people": [...],
  "products": [...],
  "unified_shopping_results": [
    {
      "category": "clothing",
      "type": "outfit",
      "search_method": "text",
      "search_query": "male black leather jacket casual",
      "products": [
        {
          "title": "Men's Black Leather Jacket",
          "price": "$299.99",
          "rating": "4.5 out of 5 stars",
          "url": "https://amazon.com/...",
          "source": "Amazon.com"
        }
      ]
    },
    {
      "category": "product",
      "type": "Pepsi bottle",
      "search_method": "visual",
      "crop_image": "final-output/image_bottle_1.png",
      "products": [
        {
          "title": "Pepsi Cola 500ml Bottle",
          "price": "$1.99",
          "source": "walmart.com",
          "thumbnail": "https://...",
          "similarity": "high"
        }
      ]
    }
  ],
  "unified_shopping_metadata": {
    "total_searches": 5,
    "text_searches": 3,
    "visual_searches": 2,
    "total_products_found": 25,
    "amazon_region": "com",
    "visual_provider": "serpapi"
  }
}
```

## Example Output

```
======================================================================
🛍️  UNIFIED SHOPPING PIPELINE
======================================================================

📄 Loaded: final-output/actor_complete_analysis_enriched.json

======================================================================
🔤 PART 1: TEXT SEARCH (Amazon)
   Best for: Clothing, accessories, style descriptions
======================================================================

🔍 Found 3 items for text search

[1/3] clothing: outfit
  🔍 Searching: male black leather jacket casual
  ✓ Found 5 products

[2/3] accessory: sunglasses
  🔍 Searching: male sunglasses
  ✓ Found 5 products

[3/3] held_item: smartphone
  🔍 Searching: male smartphone
  ✓ Found 5 products

✅ Text search complete: 3 successful searches

======================================================================
👁️  PART 2: VISUAL SEARCH (SerpAPI + Google Lens)
   Best for: Products, electronics, furniture, accessories
======================================================================

🔍 Found 2 items for visual search

[1/2] product: Pepsi bottle
  🔍 Visual search: actor_bottle_1.png
  📤 Uploading image to ImgBB...
  ✓ Uploaded to ImgBB: https://i.ibb.co/...
  🔍 Searching with Google Lens via SerpAPI...
  ✓ Found 10 visually similar products

[2/2] other_object: Necktie
  🔍 Visual search: actor_tie_1.png
  📤 Uploading image to ImgBB...
  ✓ Uploaded to ImgBB: https://i.ibb.co/...
  🔍 Searching with Google Lens via SerpAPI...
  ✓ Found 8 visually similar products

✅ Visual search complete: 2 successful searches

======================================================================
✅ UNIFIED SHOPPING COMPLETE!
======================================================================
📊 Total searches: 5
   🔤 Text searches: 3 (clothing, accessories)
   👁️  Visual searches: 2 (products, objects)
📦 Total products found: 38
📄 Saved to: final-output/actor_complete_analysis_enriched_with_unified_shopping.json
======================================================================
```

## Comparison

| Category | Text Search | Visual Search | Winner |
|----------|-------------|---------------|--------|
| Clothing | ✅ Excellent | ❌ Finds faces | Text |
| Accessories | ✅ Good | ✅ Good | Text |
| Products | ⚠️ Generic | ✅ Exact match | Visual |
| Electronics | ⚠️ Generic | ✅ Exact model | Visual |
| Furniture | ⚠️ Generic | ✅ Similar style | Visual |

## Benefits

✅ **Best of both worlds** - Uses optimal search for each category  
✅ **Higher accuracy** - Text for fashion, visual for products  
✅ **More results** - Combines both search methods  
✅ **Single command** - No need to run two separate scripts  
✅ **Organized output** - Clearly labeled by search method  

## Cost

| Service | Free Tier | Cost |
|---------|-----------|------|
| Amazon scraping | Unlimited | Free |
| SerpAPI | 100/month | $50/5000 |
| ImgBB | Unlimited | Free |

## Tips

### 1. Run After Analysis
Always run on complete analysis files with crop images

### 2. Check API Limits
- SerpAPI: 100 free searches/month
- Plan your usage accordingly

### 3. Adjust Result Limits
```bash
# Save API calls by limiting results
python3 unified_shopping.py analysis.json --max-text 3 --max-visual 5
```

### 4. Regional Shopping
```bash
# Use local Amazon for better prices
python3 unified_shopping.py analysis.json --amazon-region in
```

## Troubleshooting

### "SERPAPI_KEY required"
```bash
# Add to .env
echo "SERPAPI_KEY=your_key" >> .env
```

### "IMGBB_API_KEY not set"
```bash
# Add to .env
echo "IMGBB_API_KEY=your_key" >> .env
```

### "No crop images found"
```bash
# Run agentic pipeline first
python3 agentic_pipeline.py image.jpg
```

### Amazon Blocking
- Add delays between requests (already implemented)
- Use different regions
- Consider official APIs

## Full Pipeline Example

```bash
# Complete workflow with movie context
python3 agentic_pipeline.py actor.jpg \
  --movie "Jawan" \
  --cast "Shah Rukh Khan"

# Enrich with TMDB
python3 tmdb_enrichment.py \
  final-output/actor_complete_analysis.json

# Unified shopping (text + visual)
python3 unified_shopping.py \
  final-output/actor_complete_analysis_enriched.json

# Now you have:
# ✅ Actor identification
# ✅ Filmography
# ✅ Clothing shopping links (text search)
# ✅ Product shopping links (visual search)
```

## Summary

The unified shopping pipeline gives you the best results by using:
- **Text search** for clothing (style, color, fit)
- **Visual search** for products (exact visual match)

**Quick start:**
```bash
# 1. Setup API keys in .env
# 2. Run unified shopping
python3 unified_shopping.py final-output/analysis.json
```

Get shopping links for everything in your image! 🛍️
