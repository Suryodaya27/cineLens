import { NextRequest, NextResponse } from "next/server"

const MORE_MOVIES_API = process.env.MORE_MOVIES_API || "http://localhost:8000/api/more-movies"

export async function POST(request: NextRequest) {
	try {
		const { actor_name, limit = 10, sort_by = "rating" } = await request.json()

		if (!actor_name) {
			return NextResponse.json(
				{ error: "Actor name is required" },
				{ status: 400 }
			)
		}

		// Call the external API
		const response = await fetch(MORE_MOVIES_API, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				actor_name,
				limit,
				sort_by,
			}),
		})

		if (!response.ok) {
			throw new Error("Failed to fetch movies from external API")
		}

		const apiData = await response.json()

		return NextResponse.json({
			success: apiData.success || true,
			message: apiData.message || "",
			data: apiData.data || null,
		})
	} catch (error) {
		console.error("Error fetching more movies:", error)
		return NextResponse.json(
			{ error: error instanceof Error ? error.message : "Failed to fetch movies" },
			{ status: 500 }
		)
	}
}
