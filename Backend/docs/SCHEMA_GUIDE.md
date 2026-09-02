# Fixed JSON Schema Guide

## Overview

All output from `agentic_pipeline.py` now follows a **fixed, consistent schema**. The structure is always the same, making it easy to parse and integrate with other systems.

## Key Improvements

✅ **Always same keys**: `people`, `products`, `animals`, `vehicles`, `electronics`, `furniture`, `other_objects`  
✅ **Never missing**: Empty arrays `[]` instead of missing keys  
✅ **Gender included**: For clothing/product recommendations  
✅ **Structured clothing**: Colors, style, accessories as separate fields  
✅ **Held items as array**: Easy to extract and process  

## Fixed Structure

```json
{
  "source_image": "image.jpg",
  "scene_analysis": {
    "setting": "string",
    "lighting": "string",
    "time_of_day": "string",
    "mood": "string",
    "background_elements": ["array"],
    "composition": "string",
    "context": "string"
  },
  "detections_summary": {
    "people": 0,
    "products": 0,
    "animals": 0,
    "vehicles": 0,
    "electronics": 0,
    "furniture": 0,
    "other_objects": 0
  },
  "people": [],
  "products": [],
  "animals": [],
  "vehicles": [],
  "electronics": [],
  "furniture": [],
  "other_objects": []
}
```

## People Object Structure

```json
{
  "name": "John Doe" or null,
  "profession": "Actor" or null,
  "gender": "male|female|non-binary|unknown",
  "facial_features": "Detailed description...",
  "clothing": {
    "description": "Black leather jacket over white t-shirt",
    "colors": ["black", "white"],
    "style": "casual|formal|sporty|business|etc",
    "accessories": ["watch", "sunglasses", "jewelry"]
  },
  "pose": "Standing, facing camera",
  "expression": "Smiling confidently",
  "held_items": [
    {
      "item": "phone",
      "description": "smartphone in right hand"
    },
    {
      "item": "bottle",
      "description": "Pepsi bottle"
    }
  ],
  "confidence": 95,
  "object_class": "person",
  "crop_image": "path/to/crop.png",
  "detection_confidence": 0.98
}
```

## Products Object Structure

```json
{
  "brand": "Pepsi" or null,
  "product_type": "soda|water|wine|beer|etc",
  "size": "500ml bottle",
  "material": "plastic|glass|aluminum|etc",
  "color": ["blue", "red"],
  "label_text": "PEPSI" or null,
  "condition": "new|used|opened|sealed",
  "distinctive_features": "Classic Pepsi logo",
  "object_class": "bottle",
  "crop_image": "path/to/crop.png",
  "detection_confidence": 0.92
}
```

## Why This Matters

### 1. Easy Integration
```python
import json

with open('analysis.json') as f:
    data = json.load(f)

# Always works - no KeyError
people = data['people']  # Always exists, may be []
products = data['products']  # Always exists, may be []

# Gender for recommendations
for person in people:
    gender = person['gender']  # Always present
    colors = person['clothing']['colors']  # Always array
    style = person['clothing']['style']  # Always present
```

### 2. E-commerce Integration
```python
# Get clothing info for product recommendations
person = data['people'][0]
gender = person['gender']  # "male"
colors = person['clothing']['colors']  # ["black", "white"]
style = person['clothing']['style']  # "casual"

# Query product API
products = search_products(
    gender=gender,
    colors=colors,
    style=style
)
```

### 3. Database Storage
```sql
-- Schema matches JSON structure
CREATE TABLE people (
    name VARCHAR,
    gender VARCHAR,
    clothing_description TEXT,
    clothing_colors JSON,
    clothing_style VARCHAR,
    held_items JSON
);
```

## Validation

### Validate Existing JSON
```bash
# Fix old JSON files to match new schema
python3 schema_validator.py old_analysis.json
```

### Check Schema Compliance
```python
from schema_validator import OutputNormalizer

# Load and normalize
with open('analysis.json') as f:
    data = json.load(f)

normalized = OutputNormalizer.normalize_output(data)
# Now guaranteed to match schema
```

## Gender Values

- `"male"` - Male presentation
- `"female"` - Female presentation  
- `"non-binary"` - Non-binary presentation
- `"unknown"` - Cannot determine

## Clothing Style Values

- `"casual"` - Casual wear
- `"formal"` - Formal/business attire
- `"sporty"` - Athletic/sportswear
- `"business"` - Business casual
- `"streetwear"` - Street fashion
- `"traditional"` - Traditional/cultural dress
- `"unknown"` - Cannot determine

## Held Items Format

Always an array of objects:
```json
"held_items": [
  {"item": "guitar", "description": "acoustic guitar"},
  {"item": "microphone", "description": "handheld microphone"}
]
```

Empty if nothing held:
```json
"held_items": []
```

## Migration from Old Format

If you have old JSON files:

```bash
# Normalize all files in directory
for file in final-output/*.json; do
    python3 schema_validator.py "$file"
done
```

## Benefits Summary

| Feature | Before | After |
|---------|--------|-------|
| Consistent keys | ❌ Sometimes missing | ✅ Always present |
| Gender info | ❌ Not included | ✅ Always included |
| Clothing structure | ❌ String only | ✅ Structured object |
| Held items | ❌ String | ✅ Array of objects |
| Empty categories | ❌ Key missing | ✅ Empty array [] |
| Colors | ❌ String | ✅ Array |
| Accessories | ❌ In description | ✅ Separate array |

## Example Use Cases

### 1. Fashion Recommendations
```python
person = data['people'][0]
recommend_products(
    gender=person['gender'],
    style=person['clothing']['style'],
    colors=person['clothing']['colors']
)
```

### 2. Inventory Management
```python
# Count all detected items
summary = data['detections_summary']
total_items = sum(summary.values())
```

### 3. Person Tracking
```python
# Track who's holding what
for person in data['people']:
    name = person['name'] or "Unknown"
    items = [item['item'] for item in person['held_items']]
    print(f"{name} is holding: {', '.join(items)}")
```

### 4. Product Catalog
```python
# Extract all products with brands
products = [
    p for p in data['products'] 
    if p['brand'] is not None
]
```

## Schema File

Full JSON Schema available in: `output_schema.json`

Use with validators:
```bash
pip install jsonschema
python3 -c "
import json
from jsonschema import validate

with open('output_schema.json') as f:
    schema = json.load(f)

with open('analysis.json') as f:
    data = json.load(f)

validate(data, schema)
print('✓ Valid!')
"
```
