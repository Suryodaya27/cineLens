export interface MovieAnalysisData {
	success: boolean
	message: string
	data: {
		source_image: string
		movie_context: {
			title: string
			year: string
			cast: string[]
		}
		scene_analysis: {
			setting: string
			lighting: string
			time_of_day: string
			mood: string
			background_elements: string[]
			composition: string
			context: string
		}
		detections_summary: {
			people: number
			products: number
			animals: number
			vehicles: number
			electronics: number
			furniture: number
			other_objects: number
		}
		people: Array<{
			name: string
			profession: string
			character: string
			confidence: number
			similarity_score: number
			matched_image: string
			gender: string
			facial_features: string
			clothing: {
				description: string
				colors: string[]
				style: string
				accessories: string[]
			}
			pose: string
			expression: string
			held_items: string[]
			object_class: string
			crop_image: string
			detection_confidence: number
			crop_image_hosted: boolean
		}>
		products: any[]
		animals: any[]
		vehicles: any[]
		electronics: any[]
		furniture: any[]
		other_objects: any[]
	}
	processing_time: number
}

export function saveMovieAnalysis(movieName: string, data: MovieAnalysisData): void {
	if (typeof window !== "undefined") {
		localStorage.setItem(movieName, JSON.stringify(data))
	}
}

export function getMovieAnalysis(movieName: string): MovieAnalysisData | null {
	if (typeof window !== "undefined") {
		const data = localStorage.getItem(movieName)
		return data ? JSON.parse(data) : null
	}
	return null
}

export function getAllMovieAnalyses(): Record<string, MovieAnalysisData> {
	if (typeof window !== "undefined") {
		const analyses: Record<string, MovieAnalysisData> = {}
		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i)
			if (key) {
				const data = localStorage.getItem(key)
				if (data) {
					try {
						analyses[key] = JSON.parse(data)
					} catch (e) {
						console.error(`Failed to parse data for ${key}`, e)
					}
				}
			}
		}
		return analyses
	}
	return {}
}

export function deleteMovieAnalysis(movieName: string): void {
	if (typeof window !== "undefined") {
		localStorage.removeItem(movieName)
	}
}

// Actor Movies Cache
const ACTOR_MOVIES_PREFIX = "actor_movies_"

export interface ActorMoviesCache {
	actorName: string
	movies: string[]
	timestamp: number
	expiresIn: number // milliseconds
}

export function saveActorMovies(actorName: string, movies: string[]): void {
	if (typeof window !== "undefined") {
		const cache: ActorMoviesCache = {
			actorName,
			movies,
			timestamp: Date.now(),
			expiresIn: 24 * 60 * 60 * 1000, // 24 hours
		}
		localStorage.setItem(`${ACTOR_MOVIES_PREFIX}${actorName}`, JSON.stringify(cache))
	}
}

export function getActorMovies(actorName: string): string[] | null {
	if (typeof window !== "undefined") {
		const data = localStorage.getItem(`${ACTOR_MOVIES_PREFIX}${actorName}`)
		if (data) {
			try {
				const cache: ActorMoviesCache = JSON.parse(data)
				// Check if cache is still valid
				if (Date.now() - cache.timestamp < cache.expiresIn) {
					return cache.movies
				} else {
					// Cache expired, remove it
					localStorage.removeItem(`${ACTOR_MOVIES_PREFIX}${actorName}`)
				}
			} catch (e) {
				console.error(`Failed to parse actor movies for ${actorName}`, e)
			}
		}
	}
	return null
}

export function deleteActorMovies(actorName: string): void {
	if (typeof window !== "undefined") {
		localStorage.removeItem(`${ACTOR_MOVIES_PREFIX}${actorName}`)
	}
}

export function clearAllActorMoviesCache(): void {
	if (typeof window !== "undefined") {
		const keysToRemove: string[] = []
		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i)
			if (key && key.startsWith(ACTOR_MOVIES_PREFIX)) {
				keysToRemove.push(key)
			}
		}
		keysToRemove.forEach((key) => localStorage.removeItem(key))
	}
}