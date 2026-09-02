"use client"

import { ChevronDown, Clock, Film, Users, Eye, ShoppingBag, Clapperboard } from "lucide-react"
import { useState } from "react"
import { ThemeToggle } from "./theme-toggle"
import { getActorMovies, saveActorMovies } from "@/lib/localStorage"

interface Person {
	name: string | null
	profession?: string | null
	character?: string
	confidence: number
	similarity_score?: number
	matched_image?: string
	gender: "male" | "female" | "non-binary" | "unknown"
	facial_features: string
	clothing: {
		description: string
		colors: string[]
		style: string
		accessories: string[]
	}
	pose: string
	expression: string
	held_items: Array<{ item: string; description: string }>
	object_class: "person"
	crop_image: string
	detection_confidence: number
}

interface DetectedObject {
	[key: string]: unknown
	object_class: string
	crop_image: string
	detection_confidence: number
}

interface OutputPanelProps {
	results: {
		success?: boolean
		message?: string
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
			people: Person[]
			products: DetectedObject[]
			animals: DetectedObject[]
			vehicles: DetectedObject[]
			electronics: DetectedObject[]
			furniture: DetectedObject[]
			other_objects: DetectedObject[]
		}
		processing_time?: number
	}
}

export default function OutputPanel({ results }: OutputPanelProps) {
	const [expandedActor, setExpandedActor] = useState<number | null>(0)
	const [expandedObject, setExpandedObject] = useState<{ type: string; index: number } | null>(null)
	const [showScene, setShowScene] = useState(false)
	const [showCast, setShowCast] = useState(false)
	const [showMovies, setShowMovies] = useState(false)
	const [showShopping, setShowShopping] = useState(false)
	const [shoppingResults, setShoppingResults] = useState<any>(null)
	const [shoppingLoading, setShoppingLoading] = useState(false)
	const [actorMovies, setActorMovies] = useState<{
		actorName: string
		actorData: { profile_image?: string; biography?: string; popularity?: number } | null
		movies: Array<{
			title: string; type: string; release_date: string; character: string
			vote_average: number; poster_path: string; tmdb_id: number
		}>
		loading: boolean
	} | null>(null)

	const { data } = results
	const people = data.people || []
	const products = data.products || []
	const animals = data.animals || []
	const vehicles = data.vehicles || []
	const electronics = data.electronics || []
	const furniture = data.furniture || []
	const otherObjects = data.other_objects || []
	const scene = data.scene_analysis
	const totalObjects = products.length + animals.length + vehicles.length +
		electronics.length + furniture.length + otherObjects.length

	const fetchActorMovies = async (actorName: string) => {
		const cachedData = getActorMovies(actorName)
		if (cachedData) {
			const parsed = typeof cachedData === "string" ? JSON.parse(cachedData) : cachedData
			setActorMovies({ actorName, actorData: parsed.actorData || null, movies: parsed.movies || [], loading: false })
			setShowMovies(true)
			return
		}
		setActorMovies({ actorName, actorData: null, movies: [], loading: true })
		setShowMovies(true)
		try {
			const response = await fetch("/api/more-movies", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ actor_name: actorName, limit: 10, sort_by: "rating" }),
			})
			if (!response.ok) throw new Error("Failed to fetch movies")
			const apiResponse = await response.json()
			const movies = apiResponse.data?.movies || []
			const actorData = {
				profile_image: apiResponse.data?.profile_image,
				biography: apiResponse.data?.biography,
				popularity: apiResponse.data?.popularity,
			}
			saveActorMovies(actorName, { actorData, movies } as any)
			setActorMovies({ actorName, actorData, movies, loading: false })
		} catch {
			setActorMovies(prev => prev ? { ...prev, loading: false } : null)
		}
	}

	const fetchShopping = async () => {
		setShoppingLoading(true)
		setShowShopping(true)
		try {
			const response = await fetch("/api/shopping-recommendations", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					analysis_data: data, max_products_per_item: 5,
					max_visual_results: 10, amazon_region: "in",
				}),
			})
			if (!response.ok) throw new Error()
			const apiResponse = await response.json()
			setShoppingResults(apiResponse.data)
		} catch {
			setShoppingResults(null)
		} finally {
			setShoppingLoading(false)
		}
	}

	const Stat = ({ label, value }: { label: string; value: string | number }) => (
		<div className="text-center">
			<p className="text-2xl font-bold text-foreground">{value}</p>
			<p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-0.5">{label}</p>
		</div>
	)

	const ConfidenceBar = ({ value, label }: { value: number; label?: string }) => (
		<div className="flex items-center gap-2">
			<div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
				<div
					className="h-full bg-accent rounded-full transition-all"
					style={{ width: `${Math.min(value, 100)}%` }}
				/>
			</div>
			<span className="text-xs text-muted-foreground font-mono w-10 text-right">
				{label || `${value.toFixed(0)}%`}
			</span>
		</div>
	)

	const objectLabel = (obj: DetectedObject): string => {
		if ("product_type" in obj) return String(obj.product_type)
		if ("breed" in obj) return String(obj.breed)
		if ("make" in obj && obj.make) return `${obj.make} ${obj.model || ""}`.trim()
		if ("type" in obj) return String(obj.type)
		return obj.object_class
	}

	const renderObjects = (
		objects: DetectedObject[], title: string, icon: string, type: string
	) => {
		if (!objects.length) return null
		return (
			<div className="space-y-2">
				<h3 className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
					<span>{icon}</span> {title}
				</h3>
				{objects.map((obj, i) => (
					<div key={i} className="rounded-lg border border-border overflow-hidden">
						<button
							onClick={() => setExpandedObject(
								expandedObject?.type === type && expandedObject?.index === i
									? null : { type, index: i }
							)}
							className="w-full px-3 py-2.5 flex items-center justify-between text-left hover:bg-secondary/50 transition-colors"
						>
							<div className="flex items-center gap-2.5 min-w-0">
								<span className="text-xs font-mono text-muted-foreground w-5">{i + 1}</span>
								<span className="text-sm font-medium truncate capitalize">{objectLabel(obj)}</span>
							</div>
							<div className="flex items-center gap-2">
								<span className="text-xs text-muted-foreground font-mono">
									{(obj.detection_confidence * 100).toFixed(0)}%
								</span>
								<ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${expandedObject?.type === type && expandedObject?.index === i ? "rotate-180" : ""
									}`} />
							</div>
						</button>
						{expandedObject?.type === type && expandedObject?.index === i && (
							<div className="border-t border-border p-3 space-y-3">
								<img
									src={obj.crop_image} alt={objectLabel(obj)}
									className="w-full h-48 object-contain rounded-md bg-secondary"
								/>
								{(["material", "condition", "style", "size", "brand"] as const).map(key => {
									const val = obj[key]
									return val && typeof val === "string" ? (
										<div key={key} className="flex justify-between text-xs">
											<span className="text-muted-foreground capitalize">{key}</span>
											<span className="text-foreground capitalize">{val}</span>
										</div>
									) : null
								})}
								{"color" in obj && obj.color ? (
									<div className="flex flex-wrap gap-1">
										{(Array.isArray(obj.color) ? obj.color : [obj.color]).map((c, j) => (
											<span key={j} className="px-2 py-0.5 bg-secondary rounded text-xs capitalize">
												{String(c)}
											</span>
										))}
									</div>
								) : null}
							</div>
						)}
					</div>
				))}
			</div>
		)
	}

	return (
		<>
			<div className="flex flex-col h-full">
				{/* Header */}
				<div className="sticky top-0 z-10 px-5 py-4 bg-background/80 backdrop-blur-md border-b border-border flex items-center justify-between">
					<div className="flex items-center gap-3 min-w-0">
						<Film className="w-5 h-5 text-accent shrink-0" />
						<div className="min-w-0">
							<h2 className="text-lg font-bold truncate">{data.movie_context.title}</h2>
							<div className="flex items-center gap-3 text-xs text-muted-foreground">
								<span>{data.movie_context.year}</span>
								<span>{people.length} people</span>
								{results.processing_time && (
									<span className="flex items-center gap-1">
										<Clock className="w-3 h-3" />
										{results.processing_time.toFixed(1)}s
									</span>
								)}
							</div>
						</div>
					</div>
					<ThemeToggle />
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto">
					<div className="max-w-2xl mx-auto px-5 py-5 space-y-6">

						{/* Stats row */}
						<div className="flex items-center justify-around py-3 rounded-lg bg-secondary/50">
							<Stat label="People" value={people.length} />
							<div className="w-px h-8 bg-border" />
							<Stat label="Objects" value={totalObjects} />
							<div className="w-px h-8 bg-border" />
							<button onClick={() => setShowCast(true)} className="hover:opacity-70 transition-opacity">
								<Stat label="Cast DB" value={data.movie_context.cast.length} />
							</button>
						</div>

						{/* Scene Analysis — collapsible */}
						{scene && (
							<div className="rounded-lg border border-border">
								<button
									onClick={() => setShowScene(!showScene)}
									className="w-full px-4 py-3 flex items-center justify-between hover:bg-secondary/30 transition-colors"
								>
									<span className="flex items-center gap-2 text-sm font-medium">
										<Eye className="w-4 h-4 text-accent" /> Scene Analysis
									</span>
									<ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${showScene ? "rotate-180" : ""}`} />
								</button>
								{showScene && (
									<div className="border-t border-border px-4 py-3 grid grid-cols-2 gap-3 text-sm">
										{[
											["Setting", scene.setting],
											["Mood", scene.mood],
											["Time", scene.time_of_day],
											["Lighting", scene.lighting],
										].map(([label, val]) => val ? (
											<div key={label}>
												<p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
												<p className="text-foreground mt-0.5">{val}</p>
											</div>
										) : null)}
										{scene.context && (
											<div className="col-span-2">
												<p className="text-[10px] text-muted-foreground uppercase tracking-wider">Context</p>
												<p className="text-foreground mt-0.5">{scene.context}</p>
											</div>
										)}
									</div>
								)}
							</div>
						)}

						{/* People */}
						{people.length > 0 && (
							<div className="space-y-2">
								<h3 className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
									<Users className="w-4 h-4" /> Detected People
								</h3>
								{people.map((person, i) => (
									<div key={i} className="rounded-lg border border-border overflow-hidden">
										{/* Header */}
										<button
											onClick={() => setExpandedActor(expandedActor === i ? null : i)}
											className="w-full px-3 py-2.5 flex items-center gap-3 text-left hover:bg-secondary/30 transition-colors"
										>
											<div className="w-9 h-9 rounded-full bg-accent/15 flex items-center justify-center text-accent text-sm font-bold shrink-0">
												{i + 1}
											</div>
											<div className="flex-1 min-w-0">
												<p className="font-semibold text-sm truncate">{person.name || "Unknown"}</p>
												{person.character && (
													<p className="text-xs text-muted-foreground truncate">as {person.character}</p>
												)}
											</div>
											<div className="flex items-center gap-2 shrink-0">
												<span className={`text-xs font-mono px-1.5 py-0.5 rounded ${person.confidence >= 70 ? "bg-green-500/10 text-green-600 dark:text-green-400"
													: person.confidence >= 50 ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
														: "bg-red-500/10 text-red-600 dark:text-red-400"
													}`}>
													{person.confidence}%
												</span>
												<ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${expandedActor === i ? "rotate-180" : ""
													}`} />
											</div>
										</button>

										{/* Expanded */}
										{expandedActor === i && (
											<div className="border-t border-border p-4 space-y-4">
												{/* Crop image */}
												<img
													src={person.crop_image}
													alt={person.name || "Person"}
													className="w-full h-56 object-contain rounded-md bg-secondary"
												/>

												{/* Key stats */}
												<div className="grid grid-cols-2 gap-2">
													{[
														["Similarity", person.similarity_score ? `${(person.similarity_score * 100).toFixed(1)}%` : "—"],
														["Detection", `${(person.detection_confidence * 100).toFixed(1)}%`],
														["Gender", person.gender],
														["Profession", person.profession || "—"],
													].map(([label, val]) => (
														<div key={label} className="px-3 py-2 bg-secondary/50 rounded-md">
															<p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
															<p className="text-sm font-medium capitalize mt-0.5">{val}</p>
														</div>
													))}
												</div>

												{/* Clothing */}
												{person.clothing?.description && person.clothing.description !== "Not analyzed" && (
													<div>
														<p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Clothing</p>
														<p className="text-sm">{person.clothing.description}</p>
														{person.clothing.colors.length > 0 && (
															<div className="flex flex-wrap gap-1 mt-1.5">
																{person.clothing.colors.map((c, j) => (
																	<span key={j} className="px-2 py-0.5 bg-secondary rounded text-xs capitalize">{c}</span>
																))}
															</div>
														)}
													</div>
												)}

												{/* Pose & Expression */}
												{(person.pose !== "Not analyzed" || person.expression !== "Not analyzed") && (
													<div className="grid grid-cols-2 gap-2">
														{person.pose !== "Not analyzed" && (
															<div>
																<p className="text-[10px] text-muted-foreground uppercase tracking-wider">Pose</p>
																<p className="text-sm mt-0.5">{person.pose}</p>
															</div>
														)}
														{person.expression !== "Not analyzed" && (
															<div>
																<p className="text-[10px] text-muted-foreground uppercase tracking-wider">Expression</p>
																<p className="text-sm mt-0.5">{person.expression}</p>
															</div>
														)}
													</div>
												)}

												{/* More movies button */}
												{person.name && (
													<button
														onClick={() => fetchActorMovies(person.name!)}
														className="w-full py-2 text-sm font-medium text-accent hover:bg-accent/10 rounded-md transition-colors flex items-center justify-center gap-1.5"
													>
														<Clapperboard className="w-4 h-4" />
														More movies by {person.name}
													</button>
												)}
											</div>
										)}
									</div>
								))}
							</div>
						)}

						{/* Other objects */}
						{renderObjects(products as DetectedObject[], "Products", "🛍️", "products")}
						{renderObjects(animals as DetectedObject[], "Animals", "🐾", "animals")}
						{renderObjects(vehicles as DetectedObject[], "Vehicles", "🚗", "vehicles")}
						{renderObjects(electronics as DetectedObject[], "Electronics", "📱", "electronics")}
						{renderObjects(furniture as DetectedObject[], "Furniture", "🪑", "furniture")}
						{renderObjects(otherObjects as DetectedObject[], "Other", "📦", "other")}

						{/* Shopping button */}
						<button
							onClick={fetchShopping}
							className="w-full py-3 bg-accent text-accent-foreground font-medium rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
						>
							<ShoppingBag className="w-4 h-4" />
							Get Shopping Recommendations
						</button>
					</div>
				</div>
			</div>

			{/* === MODALS === */}

			{/* Cast Modal */}
			{showCast && (
				<div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4" onClick={() => setShowCast(false)}>
					<div className="bg-card border border-border rounded-xl max-w-lg w-full max-h-[70vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
						<div className="px-5 py-4 border-b border-border flex items-center justify-between">
							<div>
								<h3 className="font-bold">Full Cast</h3>
								<p className="text-xs text-muted-foreground">{data.movie_context.title} ({data.movie_context.year})</p>
							</div>
							<button onClick={() => setShowCast(false)} className="p-1.5 hover:bg-secondary rounded-md">
								<span className="text-lg leading-none">&times;</span>
							</button>
						</div>
						<div className="p-4 overflow-y-auto max-h-[calc(70vh-80px)]">
							<div className="grid grid-cols-2 gap-2">
								{data.movie_context.cast.map((name, i) => (
									<div key={i} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/50 text-sm">
										<span className="text-xs text-muted-foreground font-mono w-5">{i + 1}</span>
										<span className="truncate">{name}</span>
									</div>
								))}
							</div>
						</div>
					</div>
				</div>
			)}

			{/* Movies Modal */}
			{showMovies && actorMovies && (
				<div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4" onClick={() => setShowMovies(false)}>
					<div className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
						<div className="px-5 py-4 border-b border-border flex items-center justify-between">
							<div>
								<h3 className="font-bold">More Movies</h3>
								<p className="text-xs text-muted-foreground">Featuring {actorMovies.actorName}</p>
							</div>
							<button onClick={() => setShowMovies(false)} className="p-1.5 hover:bg-secondary rounded-md">
								<span className="text-lg leading-none">&times;</span>
							</button>
						</div>
						<div className="p-4 overflow-y-auto max-h-[calc(80vh-80px)]">
							{actorMovies.loading ? (
								<div className="py-12 text-center">
									<div className="w-8 h-8 mx-auto border-2 border-accent border-t-transparent rounded-full animate-spin" />
									<p className="text-sm text-muted-foreground mt-3">Loading...</p>
								</div>
							) : actorMovies.movies.length > 0 ? (
								<div className="space-y-2">
									{actorMovies.movies.map((movie, i) => (
										<div key={`${movie.tmdb_id}-${i}`} className="flex gap-3 p-3 rounded-lg border border-border hover:bg-secondary/30 transition-colors">
											{movie.poster_path ? (
												<img src={movie.poster_path} alt={movie.title} className="w-14 h-20 object-cover rounded-md shrink-0" />
											) : (
												<div className="w-14 h-20 bg-secondary rounded-md flex items-center justify-center shrink-0">
													<Film className="w-5 h-5 text-muted-foreground" />
												</div>
											)}
											<div className="flex-1 min-w-0">
												<p className="font-medium text-sm truncate">{movie.title}</p>
												<p className="text-xs text-muted-foreground">as {movie.character}</p>
												<div className="flex items-center gap-2 mt-1.5">
													<span className="text-xs bg-secondary px-1.5 py-0.5 rounded capitalize">{movie.type}</span>
													<span className="text-xs text-muted-foreground">{new Date(movie.release_date).getFullYear()}</span>
													<span className="text-xs text-accent font-medium">★ {movie.vote_average.toFixed(1)}</span>
												</div>
											</div>
										</div>
									))}
								</div>
							) : (
								<p className="text-center text-muted-foreground py-12">No movies found</p>
							)}
						</div>
					</div>
				</div>
			)}

			{/* Shopping Modal */}
			{showShopping && (
				<div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4" onClick={() => setShowShopping(false)}>
					<div className="bg-card border border-border rounded-xl max-w-5xl w-full max-h-[85vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
						<div className="px-5 py-4 border-b border-border flex items-center justify-between">
							<div>
								<h3 className="font-bold">Shopping Recommendations</h3>
								<p className="text-xs text-muted-foreground">
									{shoppingResults?.metadata?.total_products_found || 0} products found
								</p>
							</div>
							<button onClick={() => setShowShopping(false)} className="p-1.5 hover:bg-secondary rounded-md">
								<span className="text-lg leading-none">&times;</span>
							</button>
						</div>
						<div className="p-4 overflow-y-auto max-h-[calc(85vh-80px)]">
							{shoppingLoading ? (
								<div className="py-12 text-center">
									<div className="w-8 h-8 mx-auto border-2 border-accent border-t-transparent rounded-full animate-spin" />
									<p className="text-sm text-muted-foreground mt-3">Finding products...</p>
								</div>
							) : shoppingResults?.shopping_results ? (
								<div className="space-y-6">
									{shoppingResults.shopping_results.map((cat: any, ci: number) => (
										<div key={ci}>
											<div className="flex items-center gap-2 mb-3">
												<span className="text-xs font-medium bg-accent/10 text-accent px-2 py-0.5 rounded capitalize">{cat.category}</span>
												<span className="text-xs text-muted-foreground">{cat.search_method}</span>
											</div>
											<div className="grid grid-cols-2 md:grid-cols-3 gap-3">
												{cat.products.map((p: any, pi: number) => (
													<a
														key={pi} href={p.url || p.link} target="_blank" rel="noopener noreferrer"
														className="group rounded-lg border border-border overflow-hidden hover:border-accent/50 transition-colors"
													>
														<div className="h-36 bg-secondary overflow-hidden">
															{(p.image || p.thumbnail) ? (
																<img src={p.image || p.thumbnail} alt={p.title} className="w-full h-full object-contain group-hover:scale-105 transition-transform" />
															) : (
																<div className="w-full h-full flex items-center justify-center">
																	<ShoppingBag className="w-8 h-8 text-muted-foreground/30" />
																</div>
															)}
														</div>
														<div className="p-3">
															<p className="text-xs font-medium line-clamp-2">{p.title}</p>
															<div className="flex items-center justify-between mt-1.5">
																{p.price && <span className="text-sm font-bold text-accent">₹{p.price}</span>}
																{p.rating && <span className="text-xs text-muted-foreground">★ {p.rating}</span>}
															</div>
														</div>
													</a>
												))}
											</div>
										</div>
									))}
								</div>
							) : (
								<p className="text-center text-muted-foreground py-12">No products found</p>
							)}
						</div>
					</div>
				</div>
			)}
		</>
	)
}
