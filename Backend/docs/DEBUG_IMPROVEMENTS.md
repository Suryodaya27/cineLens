# Debug Output Improvements

## What Changed

### 1. Main Pipeline (`updated_agentic_pipeline.py`)

Now shows **which specific cached image** was matched:

**Before:**
```
✓ Identified: Jim Carrey (confidence: 72%)
```

**After:**
```
✓ Identified: Jim Carrey (confidence: 72%)
  Matched to: profile_2.jpg
  Full path: cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
```

**Also added to JSON output:**
```json
{
  "name": "Jim Carrey",
  "confidence": 72,
  "matched_image": "cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg",
  ...
}
```

### 2. Debug Script (`debug_face_matching.py`)

#### Test Actor Matching

**Before:**
```
Best match: profile_2.jpg
Similarity: 0.7234 (72%)
```

**After:**
```
🎯 BEST MATCH
======================================================================
File: profile_2.jpg
Full path: cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
Similarity: 0.7234 (72%)
======================================================================
✓ Would be matched with default threshold (0.6)

💡 TIP: View the matched image:
   open cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg  # macOS
   xdg-open cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg  # Linux

💡 Compare visually:
   python3 debug_face_matching.py --compare input/test.jpg "cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg"
```

#### Compare Images

**Before:**
```
Similarity Score: 0.7234 (72%)
✓ Likely the same person
```

**After:**
```
📷 Image 1: test.jpg
   Path: input/test.jpg
      ✓ Face detected (size: 180x220)

📷 Image 2: profile_2.jpg
   Path: cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
      ✓ Face detected (size: 200x240)

🎯 SIMILARITY SCORE
======================================================================
Score: 0.7234 (72%)
======================================================================
✓✓  Likely the same person
    Confidence: High (default threshold)

📊 Threshold Guide:
   • Default threshold: 0.6
   • Your similarity: 0.7234

💡 View images:
   open input/test.jpg cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg  # macOS
   xdg-open input/test.jpg && xdg-open cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg  # Linux
```

## Usage Examples

### 1. Run Pipeline and See Matched Images

```bash
python3 updated_agentic_pipeline.py input/jim.jpg --movie "Bruce Almighty"
```

Output will show:
```
[1/3] Processing person...
  ✓ Identified: Jim Carrey (confidence: 72%)
    Matched to: profile_2.jpg
    Full path: cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
```

### 2. Debug Specific Actor Match

```bash
python3 debug_face_matching.py --test-actor "Jim Carrey" input/jim.jpg
```

Shows:
- All cached images with similarity scores
- Best match with full path
- Command to view the image
- Command to compare visually

### 3. Compare Two Images Directly

```bash
python3 debug_face_matching.py --compare input/jim.jpg cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
```

Shows:
- Face detection details for both images
- Similarity score with interpretation
- Commands to view both images

### 4. View Matched Image

After seeing the match, view it:

```bash
# macOS
open cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg

# Linux
xdg-open cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
```

### 5. Check JSON Output

The matched image path is now in the JSON:

```python
import json

with open('output/image_complete_analysis.json') as f:
    data = json.load(f)

for person in data['people']:
    if person['name']:
        print(f"{person['name']}: {person['matched_image']}")
```

## Benefits

1. **Know exactly which image was matched** - No guessing
2. **Easy to verify** - View the matched image to confirm
3. **Better debugging** - Compare your input with the matched image
4. **Reproducible** - Full paths for exact reference
5. **Transparent** - See the actual cached image used

## Troubleshooting Workflow

### If match seems wrong:

1. **Check which image was matched:**
   ```bash
   python3 updated_agentic_pipeline.py input/test.jpg --movie "Movie"
   # Look for "Matched to: profile_X.jpg"
   ```

2. **View the matched image:**
   ```bash
   open cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg
   ```

3. **Compare visually:**
   ```bash
   python3 debug_face_matching.py --compare input/test.jpg "cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg"
   ```

4. **If matched image is poor quality:**
   ```bash
   # Clear cache and download more images
   python3 view_cached_actors.py --clear
   python3 updated_agentic_pipeline.py input/test.jpg --movie "Movie" --images-per-actor 10
   ```

### If no match found:

1. **Check all similarity scores:**
   ```bash
   python3 debug_face_matching.py --test-actor "Jim Carrey" input/test.jpg
   ```

2. **See which cached images exist:**
   ```bash
   ls -la cache/tmdb/actors/actor_*Jim_Carrey*/
   ```

3. **View each cached image:**
   ```bash
   open cache/tmdb/actors/actor_206_Jim_Carrey/*.jpg
   ```

4. **If best similarity is close (e.g., 0.58):**
   ```bash
   python3 updated_agentic_pipeline.py input/test.jpg --movie "Movie" --threshold 0.55
   ```

## Example Output

### Full Pipeline Run:

```
🚀 UPDATED AGENTIC PIPELINE
📷 Image: jim_carrey_test.jpg
🎬 Movie: Bruce Almighty
======================================================================

🎬 PREPARING CAST DATA: Bruce Almighty
======================================================================

🔍 Searching TMDB for: Bruce Almighty
✓ Found: Bruce Almighty (movie)
👥 Fetching cast for movie ID 310...
✓ Found 20 cast members

📸 Processing 20 cast members...

[1/20] Jim Carrey
  ✓ Using cached images from: cache/tmdb/actors/actor_206_Jim_Carrey
    Images: ['profile_0.jpg', 'profile_1.jpg', 'profile_2.jpg']
      ✓ Face detected (size: 200x240)
      ✓ Face detected (size: 180x220)
      ✓ Face detected (size: 190x230)
  ✓ Stored 3/3 face embeddings

...

======================================================================
🔍 ANALYZING IMAGE
======================================================================

🔍 Detecting people in image...
✓ Detected 1 people

👤 Identifying 1 people...

[1/1] Processing person...
    ✓ Face embedding extracted (dim: 512)
    Top 5 matches:
      ✓ 1. Jim Carrey: 0.723 (72%)
      ✓ 2. Jim Carrey: 0.689 (68%)
      ✓ 3. Jim Carrey: 0.654 (65%)
      ✗ 4. Jim Carrey: 0.582 (58%)
      ✗ 5. Jim Carrey: 0.543 (54%)
  ✓ Identified: Jim Carrey (confidence: 72%)
    Matched to: profile_2.jpg
    Full path: cache/tmdb/actors/actor_206_Jim_Carrey/profile_2.jpg

======================================================================
✅ COMPLETE!
📄 Analysis: output/jim_carrey_test_complete_analysis.json
🖼️  Crops: output/
======================================================================
```

Now you can see **exactly** which cached image was used for the match! 🎯
