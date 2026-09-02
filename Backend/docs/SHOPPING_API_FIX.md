# Shopping API Data Format Fix

## The Problem

The shopping API was receiving two different data formats:

### ✅ Correct Format (Bruce Almighty example):
```python
analysis_data = {
    'source_image': 'input_image_20251210_105418_959921.jpg',
    'movie_context': {...},
    'people': [...],
    'products': [...],
    # Direct analysis data
}
```

### ❌ Wrong Format (Ra.One example):
```python
analysis_data = {
    'success': True,
    'message': 'Image analyzed successfully',
    'analysis_data': {  # ← Actual data nested here!
        'source_image': 'input_image_20251210_210834_211917.jpg',
        'movie_context': {...},
        'people': [...],
        'products': [...],
    },
    'processing_time': 48.109759
}
```

## The Issue

The wrong format is the **complete API response** from the `/analyze` endpoint, while the shopping API expects just the **analysis data** portion.

When the shopping API tried to process the wrong format:
- It looked for `people` in the top level but found `success`, `message`, etc.
- The actual analysis data was nested inside `analysis_data` key
- This caused the shopping API to find 0 people, 0 products, etc.

## The Fix

Updated the shopping API endpoint in `api.py` to detect and handle both formats:

```python
# Handle both formats: direct analysis data or full API response
raw_data = request.analysis_data
print(f"RAW DATA STRUCTURE:")
print(f"- Keys: {list(raw_data.keys())}")

# Check if this is a full API response (has 'success', 'message', 'analysis_data')
if 'success' in raw_data and 'analysis_data' in raw_data:
    print(f"⚠️  Detected full API response format. Extracting analysis_data...")
    analysis_data = raw_data['analysis_data']
    print(f"✓ Extracted analysis data with keys: {list(analysis_data.keys())}")
else:
    print(f"✓ Direct analysis data format detected")
    analysis_data = raw_data
```

## Result

Now the shopping API works with both formats:
- **Direct analysis data**: Uses it directly
- **Full API response**: Extracts the `analysis_data` portion automatically

## How to Use

### Option 1: Send direct analysis data (recommended)
```python
payload = {
    "analysis_data": analysis_result,  # Just the analysis data
    "max_products_per_item": 5,
    "max_visual_results": 10,
    "amazon_region": "in"
}
```

### Option 2: Send full API response (now supported)
```python
payload = {
    "analysis_data": full_api_response,  # Complete /analyze response
    "max_products_per_item": 5,
    "max_visual_results": 10,
    "amazon_region": "in"
}
```

Both formats will now work correctly!