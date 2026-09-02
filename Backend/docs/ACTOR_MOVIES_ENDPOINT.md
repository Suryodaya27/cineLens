# Actor Movies Endpoint

Documentation for the `/api/more-movies` endpoint.

## Overview

The `/api/more-movies` endpoint fetches an actor's filmography from TMDB, including:
- Actor biography and details
- Profile image
- Recent or top-rated movies
- Movie posters
- Character names
- Ratings

## Endpoint

```
POST /api/more-movies
```

## Request

### Request Body

```json
{
  "actor_name": "Shah Rukh Khan",
  "limit": 10,
  "sort_by": "recent"
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `actor_name` | string | ✓ | - | Name of the actor to search for |
| `limit` | integer | | 10 | Maximum number of movies to return (1-50) |
| `sort_by` | string | | "recent" | Sort movies by "recent" or "rating" |

## Response

### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Found 10 movies for Shah Rukh Khan",
  "data": {
    "tmdb_id": 41091,
    "name": "Shah Rukh Khan",
    "known_for_department": "Acting",
    "popularity": 45.678,
    "profile_image": "https://image.tmdb.org/t/p/w500/abc123.jpg",
    "biography": "Shah Rukh Khan, also known as SRK, is an Indian actor...",
    "birthday": "1965-11-02",
    "place_of_birth": "New Delhi, India",
    "total_credits": 95,
    "movies": [
      {
        "title": "Pathaan",
        "type": "movie",
        "release_date": "2023-01-25",
        "character": "Pathaan",
        "vote_average": 7.2,
        "poster_path": "https://image.tmdb.org/t/p/w500/xyz789.jpg",
        "tmdb_id": 840326
      },
      {
        "title": "Jawan",
        "type": "movie",
        "release_date": "2023-09-07",
        "character": "Vikram Rathore / Azad",
        "vote_average": 7.0,
        "poster_path": "https://image.tmdb.org/t/p/w500/def456.jpg",
        "tmdb_id": 840326
      }
    ]
  }
}
```

### Error Response (404 Not Found)

```json
{
  "detail": "Actor not found: John Doe"
}
```

### Error Response (500 Internal Server Error)

```json
{
  "detail": "Internal server error: ..."
}
```

## Usage Examples

### cURL

#### Get Recent Movies

```bash
curl -X POST "http://localhost:8000/api/more-movies" \
  -H "Content-Type: application/json" \
  -d '{
    "actor_name": "Shah Rukh Khan",
    "limit": 10,
    "sort_by": "recent"
  }'
```

#### Get Top Rated Movies

```bash
curl -X POST "http://localhost:8000/api/more-movies" \
  -H "Content-Type: application/json" \
  -d '{
    "actor_name": "Tom Cruise",
    "limit": 15,
    "sort_by": "rating"
  }'
```

### Python

```python
import requests

# Get recent movies
response = requests.post(
    "http://localhost:8000/api/more-movies",
    json={
        "actor_name": "Shah Rukh Khan",
        "limit": 10,
        "sort_by": "recent"
    }
)

result = response.json()

if result["success"]:
    actor = result["data"]
    
    print(f"Actor: {actor['name']}")
    print(f"Total credits: {actor['total_credits']}")
    print(f"Profile: {actor['profile_image']}")
    
    print("\nMovies:")
    for movie in actor["movies"]:
        print(f"• {movie['title']} ({movie['release_date'][:4]})")
        print(f"  Rating: {movie['vote_average']}/10")
        print(f"  Character: {movie['character']}")
        print(f"  Poster: {movie['poster_path']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function getActorMovies(actorName, sortBy = 'recent') {
  try {
    const response = await axios.post('http://localhost:8000/api/more-movies', {
      actor_name: actorName,
      limit: 10,
      sort_by: sortBy
    });
    
    const { data } = response.data;
    
    console.log(`Actor: ${data.name}`);
    console.log(`Total credits: ${data.total_credits}`);
    
    console.log('\nMovies:');
    data.movies.forEach(movie => {
      console.log(`• ${movie.title} (${movie.release_date?.substring(0, 4)})`);
      console.log(`  Rating: ${movie.vote_average}/10`);
      console.log(`  Poster: ${movie.poster_path}`);
    });
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// Get recent movies
getActorMovies('Shah Rukh Khan', 'recent');

// Get top rated movies
getActorMovies('Tom Cruise', 'rating');
```

## Sort Options

### Recent (Default)

Movies are sorted by release date, with the most recent first.

```json
{
  "actor_name": "Shah Rukh Khan",
  "sort_by": "recent"
}
```

**Use case:** Find out what the actor has been working on lately.

### Rating

Movies are sorted by TMDB vote average (rating), with highest rated first.

```json
{
  "actor_name": "Shah Rukh Khan",
  "sort_by": "rating"
}
```

**Use case:** Find the actor's best-rated movies.

## Response Fields

### Actor Information

| Field | Type | Description |
|-------|------|-------------|
| `tmdb_id` | integer | TMDB person ID |
| `name` | string | Actor's name |
| `known_for_department` | string | Department (e.g., "Acting") |
| `popularity` | float | TMDB popularity score |
| `profile_image` | string (URL) | Actor's profile image URL |
| `biography` | string | Actor's biography |
| `birthday` | string | Birth date (YYYY-MM-DD) |
| `place_of_birth` | string | Birthplace |
| `total_credits` | integer | Total number of credits |

### Movie Information

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Movie or TV show title |
| `type` | string | "movie" or "tv" |
| `release_date` | string | Release date (YYYY-MM-DD) |
| `character` | string | Character name |
| `vote_average` | float | TMDB rating (0-10) |
| `poster_path` | string (URL) | Movie poster URL |
| `tmdb_id` | integer | TMDB movie/show ID |

## Image URLs

All image URLs use TMDB's image CDN:

- **Profile images**: `https://image.tmdb.org/t/p/w500/{path}`
- **Poster images**: `https://image.tmdb.org/t/p/w500/{path}`

You can change the size by replacing `w500` with:
- `w185` - Small
- `w342` - Medium
- `w500` - Large (default)
- `w780` - Extra large
- `original` - Original size

Example:
```
https://image.tmdb.org/t/p/w185/abc123.jpg  # Small
https://image.tmdb.org/t/p/original/abc123.jpg  # Original
```

## Testing

### Using the test script

```bash
python test_api.py --test-actor-movies --actor "Shah Rukh Khan"
```

### Using the example script

```bash
python example_actor_movies.py --actor "Tom Cruise" --sort rating --limit 15
```

### Using Postman

1. Import `Agentic_Pipeline_API.postman_collection.json`
2. Use "Get Actor Movies - Recent" or "Get Actor Movies - Top Rated" requests

## Error Handling

### Actor Not Found

If the actor name doesn't match any person in TMDB:

```json
{
  "detail": "Actor not found: John Doe"
}
```

**Solution:** Check the spelling or try a different name variation.

### TMDB API Error

If there's an issue with the TMDB API:

```json
{
  "detail": "Internal server error: ..."
}
```

**Solution:** Check your TMDB API key in `.env` file.

### Rate Limiting

TMDB has rate limits (40 requests per 10 seconds). If you hit the limit, wait a few seconds and retry.

## Use Cases

### 1. Actor Profile Page

Display actor information with their filmography:

```python
response = requests.post(
    "http://localhost:8000/api/more-movies",
    json={"actor_name": "Shah Rukh Khan", "limit": 20}
)

actor = response.json()["data"]

# Display profile
print(f"Name: {actor['name']}")
print(f"Bio: {actor['biography']}")
print(f"Profile: {actor['profile_image']}")

# Display movies
for movie in actor['movies']:
    print(f"{movie['title']} - {movie['vote_average']}/10")
```

### 2. Movie Recommendations

Get an actor's top-rated movies for recommendations:

```python
response = requests.post(
    "http://localhost:8000/api/more-movies",
    json={
        "actor_name": "Leonardo DiCaprio",
        "limit": 10,
        "sort_by": "rating"
    }
)

movies = response.json()["data"]["movies"]

# Show top 5 recommendations
for movie in movies[:5]:
    if movie['vote_average'] >= 7.0:
        print(f"Recommended: {movie['title']} ({movie['vote_average']}/10)")
```

### 3. Recent Work

Check what an actor has been working on recently:

```python
response = requests.post(
    "http://localhost:8000/api/more-movies",
    json={
        "actor_name": "Tom Cruise",
        "limit": 5,
        "sort_by": "recent"
    }
)

movies = response.json()["data"]["movies"]

print("Recent movies:")
for movie in movies:
    year = movie['release_date'][:4] if movie['release_date'] else 'TBA'
    print(f"• {movie['title']} ({year})")
```

## Performance

- **Average response time**: 1-3 seconds
- **TMDB API calls**: 3 per request (search, details, credits)
- **Rate limit**: 40 requests per 10 seconds (TMDB limit)

## Related Endpoints

- `POST /analyze` - Analyze image and identify actors
- `GET /health` - Check API health

## Support

For issues:
1. Check TMDB API key is configured in `.env`
2. Verify actor name spelling
3. Check API logs for detailed errors
4. Review TMDB API documentation: https://developers.themoviedb.org/
