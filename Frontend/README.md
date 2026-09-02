# Movie Frame Analyzer

AI-powered actor detection from movie frames built with Next.js.

## Features

- **Image URL Input**: Provide an image URL to download and analyze
- **File Upload**: Upload image files directly from your device
- **ImageBB Integration**: Automatically uploads images to ImageBB for hosting
- **API Integration**: Sends image URL and movie details to your backend API
- **LocalStorage**: Saves analysis results with movie name as key for quick retrieval

## How It Works

1. User provides a movie name and frame image (via URL or file upload)
2. Image is downloaded (if URL) or converted to base64 (if file)
3. Image is uploaded to ImageBB for hosting
4. API request is sent with ImageBB URL and movie details
5. Analysis results are saved to localStorage with movie name as key

## Setup

1. Get an ImageBB API key from [https://api.imgbb.com/](https://api.imgbb.com/)
2. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
3. Add your credentials to `.env.local`:
   ```
   IMGBB_API_KEY=your_imgbb_api_key
   YOUR_API_ENDPOINT=https://your-api.com/analyze
   ```

## API Integration

The API route sends this payload to your endpoint (`http://localhost:8000/analyze`):

```json
{
  "image_url": "https://i.ibb.co/xxx/image.jpg",
  "movie_name": "ra.one",
  "enable_vision": 1,
  "similarity_threshold": 0.5,
  "max_cast": 10,
  "vision_model": "qwen3-vl:8b"
}
```

The API response is automatically saved to localStorage with the movie name as the key.

## LocalStorage

Results are stored in localStorage for quick access:
- **Key**: Movie name (e.g., "ra.one")
- **Value**: Complete API response with scene analysis, detected people, and metadata

Use the utility functions in `lib/localStorage.ts`:
```typescript
import { getMovieAnalysis, getAllMovieAnalyses } from '@/lib/localStorage'

// Get specific movie analysis
const analysis = getMovieAnalysis('ra.one')

// Get all stored analyses
const allAnalyses = getAllMovieAnalyses()
```

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

- `app/page.tsx` - Main page component with localStorage integration
- `components/input-panel.tsx` - Image input and movie name form
- `components/output-panel.tsx` - Results display
- `app/api/analyze-movie/route.ts` - API route for ImageBB upload and analysis
- `lib/localStorage.ts` - LocalStorage utility functions


## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs)
- [Learn Next.js](https://nextjs.org/learn)
