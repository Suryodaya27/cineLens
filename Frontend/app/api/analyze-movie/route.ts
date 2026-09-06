import { NextRequest, NextResponse } from "next/server"

const IMGBB_API_KEY = process.env.IMGBB_API_KEY || "11256c78854542733cb29769b5d50316"
const API_STREAM_ENDPOINT = process.env.API_ENDPOINT
	? process.env.API_ENDPOINT.replace(/\/analyze$/, "/analyze-stream")
	: "http://localhost:8000/analyze-stream"

async function uploadToImageBB(base64Image: string): Promise<string> {
	const formData = new FormData()
	formData.append("image", base64Image)

	const response = await fetch(
		`https://api.imgbb.com/1/upload?key=${IMGBB_API_KEY}`,
		{
			method: "POST",
			body: formData,
		}
	)

	if (!response.ok) {
		throw new Error("Failed to upload to ImageBB")
	}

	const data = await response.json()
	return data.data.url
}

export async function POST(request: NextRequest) {
	try {
		const { imageUrl, imageFile, movieName } = await request.json()

		let base64Image: string

		if (imageUrl && !imageFile) {
			const response = await fetch(imageUrl)
			if (!response.ok) {
				throw new Error("Failed to download image")
			}
			const buffer = await response.arrayBuffer()
			base64Image = Buffer.from(buffer).toString("base64")
		} else if (imageFile) {
			base64Image = imageFile.split(",")[1]
		} else {
			return NextResponse.json(
				{ error: "No image provided" },
				{ status: 400 }
			)
		}

		// Upload to ImageBB first (quick step, not streamed)
		const imageBBUrl = await uploadToImageBB(base64Image)
		console.log("ImageBB URL:", imageBBUrl)
		console.log("Movie Name:", movieName)

		// Open SSE stream to backend
		const backendResponse = await fetch(API_STREAM_ENDPOINT, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				image_url: imageBBUrl,
				movie_name: movieName,
				enable_vision: 1,
				similarity_threshold: 0.45,
				max_cast: 10,
			}),
		})

		if (!backendResponse.ok || !backendResponse.body) {
			const errorBody = await backendResponse.text().catch(() => "no body")
			throw new Error(`Backend returned ${backendResponse.status}: ${errorBody}`)
		}

		// Proxy the SSE stream straight through to the browser.
		// We inject an initial "imagebb" event so the client has the hosted URL.
		const encoder = new TextEncoder()
		const backendStream = backendResponse.body

		const stream = new ReadableStream({
			async start(controller) {
				// Send imagebb url as first event
				const initEvent = `event: imagebb\ndata: ${JSON.stringify({ imageBBUrl, movieName })}\n\n`
				controller.enqueue(encoder.encode(initEvent))

				const reader = backendStream.getReader()
				try {
					while (true) {
						const { done, value } = await reader.read()
						if (done) break
						controller.enqueue(value)
					}
				} finally {
					controller.close()
				}
			},
		})

		return new Response(stream, {
			headers: {
				"Content-Type": "text/event-stream",
				"Cache-Control": "no-cache",
				Connection: "keep-alive",
			},
		})
	} catch (error) {
		console.error("Error processing image:", error)
		return NextResponse.json(
			{ error: error instanceof Error ? error.message : "Failed to process image" },
			{ status: 500 }
		)
	}
}
