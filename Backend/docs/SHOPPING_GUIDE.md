# Amazon Shopping Integration Guide

## Overview

Automatically find products on Amazon based on your image analysis. Searches for clothing, furniture, electronics, products, and accessories detected in the image.

## Installation

```bash
pip install beautifulsoup4 lxml requests
# or
pip install -r requirements.txt
```

## Complete Workflow

```bash
# Step 1: Analyze image
python3 agentic_pipeline.py actor_photo.jpg

# Step 2: Enrich with TMDB (optional)
python3 tmdb_enrichment.py final-output/actor_photo_complete_analysis.json

# Step 3: Find products on Amazon
python3 amazon_shopping.py final-output/actor_photo_complete_analysis_enriched.json
```

## Basic Usage

```bash
python3 amazon_shopping.py final-output/your_analysis_enriched.json
```

## What It Searches For

### From People:
- **Clothing**: "men black leather jacket casual"
- **Accessories**: "men sunglasses", "women watch"
- **Style items**: Based on detected fashion

### From Products:
- **Branded items**: "Pepsi soda", "Coca-Cola bottle"
- **Generic products**: "water bottle", "coffee cup"

### From Electronics:
- **Devices**: "Apple iPhone", "MacBook Pro"
- **Gadgets**: "laptop", "smartphone"

### From Furniture:
- **Items**: "wooden chair modern", "leather couch"

### From Other Objects:
- **Miscellaneous**: Any other detected items

## Advanced Options

### Different Amazon Regions

```bash
# Amazon India
python3 amazon_shopping.py analysis.json --region in

# Amazon UK
python3 amazon_shopping.py analysis.json --region co.uk

# Amazon Germany
python3 amazon_shopping.py analysis.json --region de
```

### Limit Products

```bash
# Get only 3 products per item (faster)
python3 amazon_shopping.py analysis.json --max-products 3

# Get 10 products per item (more options)
python3 amazon_shopping.py analysis.json --max-products 10
```

### Custom Output

```bash
python3 amazon_shopping.py analysis.json -o my_shopping_results.json
```

### View Summary Only

```bash
# For already enriched files
python3 amazon_shopping.py analysis_with_shopping.json --summary
```

## Output Structure

```json
{
  "people": [...],
  "products": [...],
  "shopping_recommendations": [
    {
      "category": "clothing",
      "type": "outfit",
      "search_query": "men black leather jacket casual",
      "products": [
        {
          "title": "Men's Black Leather Jacket...",
          "price": "199.99",
          "rating": "4.5 out of 5 stars",
          "reviews": "1,234",
          "url": "https://amazon.com/...",
          "image": "https://...",
          "source": "Amazon.com"
        }
      ]
    },
    {
      "category": "product",
      "type": "soda",
      "search_query": "Pepsi soda",
      "products": [...]
    }
  ],
  "shopping_metadata": {
    "total_searches": 5,
    "successful_searches": 4,
    "total_products_found": 20,
    "amazon_region": "com"
  }
}
```

## Example Output

```
==================================================================
🛒 AMAZON SHOPPING INTEGRATION
==================================================================

📄 Loaded: final-output/actor_complete_analysis_enriched.json

🔍 Found 5 searchable items

[1/5] clothing: outfit
  🔍 Searching: men black leather jacket casual
  ✓ Found 5 products

[2/5] accessory: sunglasses
  🔍 Searching: men sunglasses
  ✓ Found 5 products

[3/5] product: soda
  🔍 Searching: Pepsi soda
  ✓ Found 5 products

==================================================================
✅ SHOPPING INTEGRATION COMPLETE!
📊 Searched: 5 items
📦 Found: 15 products
📄 Saved to: final-output/actor_complete_analysis_enriched_with_shopping.json
==================================================================

==================================================================
🛒 SHOPPING RECOMMENDATIONS SUMMARY
==================================================================

📦 CLOTHING: outfit
   Search: men black leather jacket casual
   Found 5 products:

   1. Men's Classic Black Leather Jacket - Genuine Leather...
      Price: $199.99
      Rating: 4.5 out of 5 stars
      URL: https://amazon.com/...

   2. Casual Black Faux Leather Jacket for Men...
      Price: $89.99
      Rating: 4.3 out of 5 stars
      URL: https://amazon.com/...
```

## Use Cases

### 1. Fashion Recommendations
Get shopping links for detected clothing styles

### 2. Product Discovery
Find exact products or similar items

### 3. Price Comparison
See multiple options and prices

### 4. Affiliate Marketing
Add affiliate tags to URLs for commissions

### 5. E-commerce Integration
Integrate with your own store

## Important Notes

### ⚠️ Legal Considerations

**Web scraping may violate Amazon's Terms of Service.**

**Alternatives:**
1. **Amazon Product Advertising API** (official, requires approval)
2. **Affiliate APIs** (legal, earn commissions)
3. **Use for personal/research only**

### Rate Limiting

The script includes:
- Random delays (1-2 seconds between requests)
- Realistic browser headers
- Polite scraping practices

**Still, use responsibly:**
- Don't run on hundreds of images at once
- Add longer delays if needed
- Consider official APIs for production

### Blocking Prevention

If Amazon blocks you:
1. Increase delays: Edit `time.sleep(random.uniform(2, 4))`
2. Use proxies (not included)
3. Switch to official API

## Integration with Workflow

### Complete Pipeline

```bash
# 1. Analyze image with movie context
python3 agentic_pipeline.py actor.jpg \
  --movie "Jawan" \
  --cast "Shah Rukh Khan"

# 2. Enrich with TMDB filmography
python3 tmdb_enrichment.py \
  final-output/actor_complete_analysis.json

# 3. Add shopping recommendations
python3 amazon_shopping.py \
  final-output/actor_complete_analysis_enriched.json

# Final output: actor_complete_analysis_enriched_with_shopping.json
```

### Batch Processing

```bash
# Process multiple images
for file in final-output/*_enriched.json; do
  python3 amazon_shopping.py "$file"
  sleep 5  # Be polite between files
done
```

## Customization

### Add Affiliate Tags

Edit `amazon_shopping.py` and modify URL generation:

```python
# Add your affiliate tag
url = f"{self.base_url}{link_elem['href']}&tag=your-affiliate-tag"
```

### Filter by Price Range

Add price filtering in `_parse_product`:

```python
if price and float(price.replace(',', '')) > 100:
    return None  # Skip expensive items
```

### Custom Search Queries

Modify `build_search_query` to customize how queries are built.

## Troubleshooting

### "No products found"
- Amazon may be blocking
- Try different region: `--region in`
- Check internet connection
- Increase delays in code

### "Connection timeout"
- Check internet connection
- Amazon may be slow
- Increase timeout in code

### "Parsing errors"
- Amazon changed their HTML structure
- Update BeautifulSoup selectors
- Consider official API

## Tips

### 1. Use Enriched Analysis
Always run on `_enriched.json` files for best results

### 2. Regional Differences
- US: `--region com`
- India: `--region in` (better for Indian brands)
- UK: `--region co.uk`

### 3. Limit Products
Start with `--max-products 3` for faster testing

### 4. Check Results
Review `_with_shopping.json` to see what was found

### 5. Be Respectful
- Don't abuse the scraper
- Add delays between requests
- Consider official APIs for production

## Future Enhancements

Possible additions:
- [ ] Multiple store support (eBay, Walmart)
- [ ] Price tracking over time
- [ ] Product comparison
- [ ] Affiliate link generation
- [ ] Image similarity matching
- [ ] Official API integration

## Summary

✅ **Automatic product search** from image analysis  
✅ **Multiple categories** (clothing, electronics, furniture)  
✅ **Smart query building** based on detected attributes  
✅ **Regional support** (US, India, UK, etc.)  
✅ **Easy integration** with existing pipeline  
⚠️ **Use responsibly** - consider official APIs for production  

**Quick command:**
```bash
python3 amazon_shopping.py final-output/analysis_enriched.json
```
