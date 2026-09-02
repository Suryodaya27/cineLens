import { NextRequest, NextResponse } from "next/server"

const SHOPPING_API = process.env.SHOPPING_API || "http://localhost:8000/api/shopping-recommendations"

export async function POST(request: NextRequest) {
	try {
		const requestBody = await request.json()
		console.log("Shopping API received request body:", JSON.stringify(requestBody, null, 2))

		const {
			analysis_data,
			max_products_per_item = 5,
			max_visual_results = 10,
			amazon_region = "in",
		} = requestBody

		if (!analysis_data) {
			console.error("No analysis_data provided in request")
			return NextResponse.json(
				{ error: "Analysis data is required" },
				{ status: 400 }
			)
		}

		console.log("Analysis data structure:", {
			hasMovieContext: !!analysis_data.movie_context,
			hasPeople: !!analysis_data.people,
			hasProducts: !!analysis_data.products,
			peopleCount: analysis_data.people?.length || 0,
			productsCount: analysis_data.products?.length || 0
		})

		// Prepare data for external API
		const externalApiData = {
			analysis_data,
			max_products_per_item,
			max_visual_results,
			amazon_region,
		}

		console.log("Sending to external API:", SHOPPING_API)
		console.log("External API payload:", JSON.stringify(externalApiData, null, 2))

		// Call the external API
		const response = await fetch(SHOPPING_API, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(externalApiData),
		})

		if (!response.ok) {
			const errorText = await response.text()
			console.error("External API error:", {
				status: response.status,
				statusText: response.statusText,
				body: errorText
			})
			throw new Error(`External API failed: ${response.status} ${response.statusText} - ${errorText}`)
		}

		const apiData = await response.json()

		return NextResponse.json({
			success: apiData.success || true,
			message: apiData.message || "",
			data: apiData.data || null,
		})
	} catch (error) {
		console.error("Error fetching shopping recommendations:", error)
		return NextResponse.json(
			{
				error: error instanceof Error ? error.message : "Failed to fetch shopping recommendations",
			},
			{ status: 500 }
		)
	}
}
