# TMDB Enrichment Guide

## Overview

After running the agentic pipeline, enrich your analysis with actor filmography from TMDB (The Movie Database). This adds:
- Recent movies/shows
- Total filmography count
- Character names
- Ratings
- Biography
- Profile images

## Setup

### 1. Get TMDB API Key (Free)

1. Go to https://www.themoviedb.org/signup
2. Create free account
3. Go to https://www.themoviedb.org/settings/api
4. Request API key (choose "Developer")
5. Copy your API key

### 2. Set API Key

```bash
# Option 1: .env file (RECOMMENDED - persistent)
cp .env.example .env
# Edit .env and add: TMDB_API_KEY=your_key_here

# Option 2: Environment variable (temporary)
export TMDB_API_KEY=your_api_key_here

# Option 3: Pass as argument (one-time)
python3 tmdb_enrichment.py analysis.json --api-key your_key_here
```

### 3. Install Requirements

```bash
pip install requests python-dotenv
# or
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# 1. Run agentic pipeline
python3 agentic_pipeline.py actor_image.jpg

# 2. Enrich with TMDB data
export TMDB_API_KEY=your_key_here
python3 tmdb_enrichment.py final-output/actor_image_complete_analysis.json
```

### Advanced Options

```bash
# Specify output file
python3 tmdb_enrichment.py analysis.json -o enriched_analysis.json

# Limit to 5 recent movies per actor
python3 tmdb_enrichment.py analysis.json --max-credits 5

# Show filmography summary only (for already enriched files)
python3 tmdb_enrichment.py analysis_enriched.json --summary
```

## Complete Workflow

```bash
# Step 1: Analyze image
python3 agentic_pipeline.py srk_photo.jpg \
  --movie "Jawan" \
  --cast "Shah Rukh Khan" Nayanthara

# Step 2: Enrich with TMDB
export TMDB_API_KEY=your_key_here
python3 tmdb_enrichment.py \
  final-output/srk_photo_complete_analysis.json

# Step 3: View enriched data
cat final-output/srk_photo_complete_analysis_enriched.json
```

## Output Structure

### Before Enrichment
```json
{
  "people": [{
    "name": "Shah Rukh Khan",
    "profession": "Actor",
    "gender": "male"
  }]
}
```

### After Enrichment
```json
{
  "people": [{
    "name": "Shah Rukh Khan",
    "profession": "Actor",
    "gender": "male",
    "tmdb_data": {
      "tmdb_id": 33196,
      "name": "Shah Rukh Khan",
      "known_for_department": "Acting",
      "popularity": 45.678,
      "profile_image": "https://image.tmdb.org/t/p/w500/...",
      "biography": "Shah Rukh Khan, also known as SRK...",
      "birthday": "1965-11-02",
      "place_of_birth": "New Delhi, India",
      "total_credits": 120,
      "recent_movies": [
        {
          "title": "Jawan",
          "type": "movie",
          "release_date": "2023-09-07",
          "character": "Azad / Vikram Rathore",
          "vote_average": 7.2,
          "poster_path": "https://image.tmdb.org/t/p/w500/...",
          "tmdb_id": 840326
        },
        {
          "title": "Pathaan",
          "type": "movie",
          "release_date": "2023-01-25",
          "character": "Pathaan",
          "vote_average": 7.0,
          "poster_path": "https://image.tmdb.org/t/p/w500/...",
          "tmdb_id": 840326
        }
      ]
    }
  }]
}
```

## Example Output

```
==================================================================
🎬 TMDB ENRICHMENT
==================================================================

📄 Loaded: final-output/srk_photo_complete_analysis.json

👥 Enriching 1 people with TMDB data...

[1/1] Shah Rukh Khan
  🔍 Searching TMDB for: Shah Rukh Khan
  ✓ Found: Shah Rukh Khan (ID: 33196)
  ✓ Added 10 recent credits

==================================================================
✅ ENRICHMENT COMPLETE!
📄 Saved to: final-output/srk_photo_complete_analysis_enriched.json
==================================================================

==================================================================
🎬 ACTOR FILMOGRAPHY SUMMARY
==================================================================

🎭 Shah Rukh Khan
   Known for: Acting
   Total credits: 120
   Birthday: 1965-11-02

   Recent Movies/Shows:
   1. Jawan (2023)
      Character: Azad / Vikram Rathore
      Rating: ⭐ 7.2/10
   2. Pathaan (2023)
      Character: Pathaan
      Rating: ⭐ 7.0/10
   3. Dunki (2023)
      Character: Hardayal Singh Dhillon
      Rating: ⭐ 6.8/10
   4. Zero (2018)
      Character: Bauua Singh
      Rating: ⭐ 5.2/10
   5. Raees (2017)
      Character: Raees Alam
      Rating: ⭐ 6.9/10
```

## Batch Processing

```bash
# Enrich multiple analysis files
for file in final-output/*_complete_analysis.json; do
  python3 tmdb_enrichment.py "$file"
done
```

## Use Cases

### 1. Actor Discovery
Find what else an actor has been in:
```python
import json

with open('analysis_enriched.json') as f:
    data = json.load(f)

for person in data['people']:
    tmdb = person.get('tmdb_data')
    if tmdb:
        print(f"{tmdb['name']} - Recent movies:")
        for movie in tmdb['recent_movies'][:5]:
            print(f"  • {movie['title']} ({movie['release_date'][:4]})")
```

### 2. Recommendation System
Recommend similar content:
```python
# Get all movies from identified actors
all_movies = []
for person in data['people']:
    if person.get('tmdb_data'):
        all_movies.extend(person['tmdb_data']['recent_movies'])

# Sort by rating
top_movies = sorted(all_movies, key=lambda x: x['vote_average'], reverse=True)
```

### 3. Database Population
Store actor filmography in database:
```python
for person in data['people']:
    tmdb = person.get('tmdb_data')
    if tmdb:
        db.insert_actor({
            'name': tmdb['name'],
            'tmdb_id': tmdb['tmdb_id'],
            'biography': tmdb['biography'],
            'total_credits': tmdb['total_credits']
        })
        
        for movie in tmdb['recent_movies']:
            db.insert_movie({
                'actor_id': tmdb['tmdb_id'],
                'title': movie['title'],
                'release_date': movie['release_date'],
                'rating': movie['vote_average']
            })
```

## API Rate Limits

TMDB free tier limits:
- 40 requests per 10 seconds
- Plenty for normal use

The enricher automatically handles:
- One person at a time (sequential)
- Reasonable timeouts
- Error handling

## Troubleshooting

### "TMDB API key required"
```bash
# Set environment variable
export TMDB_API_KEY=your_key_here

# Or pass as argument
python3 tmdb_enrichment.py analysis.json --api-key your_key
```

### "Not found on TMDB"
- Actor name might be spelled differently
- Try editing the name in analysis JSON before enriching
- Some regional actors might not be in TMDB

### "Error getting credits"
- Check internet connection
- Verify API key is valid
- Check TMDB API status: https://status.themoviedb.org/

## Integration with E-commerce

Use filmography for product recommendations:

```python
# Get actor's recent movies
actor_movies = person['tmdb_data']['recent_movies']

# Recommend merchandise
for movie in actor_movies[:3]:
    products = search_products(
        query=f"{movie['title']} merchandise",
        category="movies"
    )
```

## Tips

### 1. Enrich After Analysis
Always run agentic pipeline first, then enrich:
```bash
python3 agentic_pipeline.py image.jpg
python3 tmdb_enrichment.py final-output/image_complete_analysis.json
```

### 2. Adjust Credit Limit
For quick overview, use fewer credits:
```bash
python3 tmdb_enrichment.py analysis.json --max-credits 5
```

For comprehensive filmography:
```bash
python3 tmdb_enrichment.py analysis.json --max-credits 20
```

### 3. Cache Results
Enriched files can be reused - no need to re-enrich:
```bash
# Just show summary from enriched file
python3 tmdb_enrichment.py analysis_enriched.json --summary
```

### 4. Verify Names
If actor not found, check the name in analysis JSON:
```bash
# View detected names
cat final-output/analysis.json | grep '"name"'

# Edit if needed before enriching
```

## Complete Example

```bash
# 1. Analyze image with movie context
python3 agentic_pipeline.py leo_scene.jpg \
  --movie-json example_movie_contexts/leo.json

# 2. Set TMDB API key
export TMDB_API_KEY=abc123xyz789

# 3. Enrich with filmography
python3 tmdb_enrichment.py \
  final-output/leo_scene_complete_analysis.json \
  --max-credits 10

# 4. View results
cat final-output/leo_scene_complete_analysis_enriched.json

# 5. Show summary
python3 tmdb_enrichment.py \
  final-output/leo_scene_complete_analysis_enriched.json \
  --summary
```

## Benefits

✅ **Complete actor profiles** - Biography, birthday, birthplace  
✅ **Recent filmography** - Last 10-20 movies/shows  
✅ **Ratings included** - TMDB community ratings  
✅ **Character names** - What role they played  
✅ **Profile images** - High-quality actor photos  
✅ **Total credits** - Complete filmography count  
✅ **Free API** - No cost for personal use  

## Summary

1. Get free TMDB API key
2. Run agentic pipeline on image
3. Enrich analysis with TMDB data
4. Get complete actor filmography
5. Use for recommendations, discovery, or database

**Quick command:**
```bash
export TMDB_API_KEY=your_key
python3 tmdb_enrichment.py final-output/analysis.json
```
