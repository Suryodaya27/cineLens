# Debugging Face Matching Issues

If actors aren't being matched correctly (like Jim Carrey), use these tools to diagnose the problem.

## Quick Diagnosis

### Step 1: Check if face is detected

```bash
python3 debug_face_matching.py --test-detection input/jim_carrey.jpg
```

This will tell you:
- ✓ If a face is detected
- Image size and face size
- Embedding quality

**Common issues:**
- Face too small (< 50x50 pixels)
- Face at extreme angle
- Poor image quality
- Face partially occluded

### Step 2: Check cached actor embeddings

```bash
python3 debug_face_matching.py --list-actors
```

This shows all actors with cached embeddings. Make sure "Jim Carrey" is in the list.

### Step 3: Test matching against cached embeddings

```bash
python3 debug_face_matching.py --test-actor "Jim Carrey" input/jim_carrey.jpg
```

This will:
- Show all cached images for Jim Carrey
- Compare your test image against each cached image
- Show similarity scores
- Tell you what threshold to use

**Example output:**
```
Comparing against 5 cached images:
======================================================================
✓ profile_0.jpg: 0.7234 (72%)
✓ profile_1.jpg: 0.6891 (68%)
✓ profile_2.jpg: 0.6543 (65%)
✗ profile_3.jpg: 0.5821 (58%)
✗ profile_4.jpg: 0.5432 (54%)

Best match: profile_0.jpg
Similarity: 0.7234 (72%)
✓ Would be matched with default threshold (0.6)
```

### Step 4: Compare two images directly

```bash
python3 debug_face_matching.py --compare input/jim1.jpg input/jim2.jpg
```

This calculates the similarity between two specific images.

## Common Issues and Solutions

### Issue 1: No face detected in cached images

**Symptom:**
```
⚠️  No faces detected in any of the 5 images
```

**Solution:**
```bash
# Download more images per actor
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie" \
  --images-per-actor 10
```

### Issue 2: Similarity below threshold

**Symptom:**
```
❌ No match above threshold 0.6
Top 5 matches:
  ✗ 1. Jim Carrey: 0.582 (58%)
  ✗ 2. Other Actor: 0.521 (52%)
```

**Solution:**
```bash
# Lower the threshold
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie" \
  --threshold 0.55
```

**Recommended thresholds:**
- `0.7-0.8`: Very strict (few false positives, may miss some)
- `0.6`: Balanced (default, recommended)
- `0.5-0.55`: Lenient (more matches, some false positives)
- `0.4-0.45`: Very lenient (many false positives)

### Issue 3: Face too small in cropped image

**Symptom:**
```
⚠️  No face detected in crop (size: 80x120)
```

**Solution:**
The YOLO detection might be cropping too tightly. The pipeline already adds 20% padding, but you can manually adjust the crop if needed.

### Issue 4: Wrong actor matched

**Symptom:**
Jim Carrey is matched as someone else.

**Diagnosis:**
```bash
# Check what the similarity scores are
python3 debug_face_matching.py --test-actor "Jim Carrey" input/jim.jpg
python3 debug_face_matching.py --test-actor "Other Actor" input/jim.jpg
```

If Jim Carrey has lower similarity than another actor, the cached images might be poor quality.

**Solution:**
```bash
# Clear cache and re-download
python3 view_cached_actors.py --clear

# Re-run with more images
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie" \
  --images-per-actor 10
```

### Issue 5: Actor not in TMDB cast list

**Symptom:**
Actor doesn't appear in the cached actors list.

**Solution:**
Check if the actor is in the TMDB cast for that movie:
1. Visit https://www.themoviedb.org/
2. Search for the movie
3. Check the cast list
4. If actor is missing, they won't be matched

## Viewing Cached Data

### View all cached images

```bash
python3 view_cached_actors.py
```

This shows:
- All cached actor images
- Where they're stored (`cache/tmdb/actors/`)
- Database embeddings

### View specific actor's images

```bash
ls -la cache/tmdb/actors/actor_*Jim_Carrey*/
```

### Clear cache and start fresh

```bash
python3 view_cached_actors.py --clear
```

## Advanced Debugging

### Check database embeddings

```bash
python3 view_cached_actors.py --db-only
```

### Manual similarity calculation

```python
from debug_face_matching import compare_embeddings

# Compare two images
compare_embeddings("input/jim1.jpg", "input/jim2.jpg")
```

### Check InsightFace model

```python
from updated_agentic_pipeline import InsightFaceRecognizer

recognizer = InsightFaceRecognizer()
embedding = recognizer.extract_embedding("input/image.jpg", debug=True)
print(f"Embedding shape: {embedding.shape if embedding is not None else 'None'}")
```

## Improving Match Accuracy

### 1. Use more profile images

```bash
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie" \
  --images-per-actor 10
```

More images = better embeddings = higher accuracy

### 2. Adjust threshold based on your needs

```bash
# Strict (fewer false positives)
--threshold 0.7

# Balanced (default)
--threshold 0.6

# Lenient (more matches)
--threshold 0.5
```

### 3. Use higher quality input images

- Larger face size (> 100x100 pixels)
- Good lighting
- Front-facing or slight angle
- Minimal occlusion

### 4. Process more cast members

```bash
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie" \
  --max-cast 30
```

Default is 20, but some movies have large casts.

## Understanding Similarity Scores

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0.8 - 1.0 | Very high confidence | Definitely same person |
| 0.7 - 0.8 | High confidence | Very likely same person |
| 0.6 - 0.7 | Good confidence | Likely same person (default threshold) |
| 0.5 - 0.6 | Moderate confidence | Possibly same person |
| 0.4 - 0.5 | Low confidence | Unlikely same person |
| 0.0 - 0.4 | Very low confidence | Different people |

## Example Workflow: Debugging Jim Carrey

```bash
# 1. Check if Jim Carrey is cached
python3 debug_face_matching.py --list-actors | grep -i "jim"

# 2. If not cached, run pipeline first
python3 updated_agentic_pipeline.py input/jim.jpg --movie "Bruce Almighty"

# 3. Test matching
python3 debug_face_matching.py --test-actor "Jim Carrey" input/jim.jpg

# 4. If similarity is low (e.g., 0.58), lower threshold
python3 updated_agentic_pipeline.py input/jim.jpg \
  --movie "Bruce Almighty" \
  --threshold 0.55

# 5. If still not working, try more images
python3 view_cached_actors.py --clear
python3 updated_agentic_pipeline.py input/jim.jpg \
  --movie "Bruce Almighty" \
  --images-per-actor 10 \
  --threshold 0.55
```

## Getting Help

If you're still having issues:

1. Run the debug script and save output:
   ```bash
   python3 debug_face_matching.py --test-actor "Actor Name" input/image.jpg > debug.txt
   ```

2. Check the similarity scores in the output

3. Adjust threshold accordingly

4. If all similarities are very low (< 0.4), the cached images might be poor quality

## Tips

- ✅ Use high-quality input images
- ✅ Ensure faces are clearly visible
- ✅ Try different threshold values
- ✅ Use more profile images per actor
- ✅ Clear cache if images seem wrong
- ❌ Don't use threshold below 0.4 (too many false positives)
- ❌ Don't use images with multiple faces (YOLO will crop them separately)
