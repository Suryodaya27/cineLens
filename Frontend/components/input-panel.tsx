"use client"

import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload, Link2, Film, Clapperboard } from "lucide-react"

interface InputPanelProps {
	onAnalyze: (imageData: string, movieName: string, isFile: boolean) => void
	isLoading: boolean
}

export default function InputPanel({ onAnalyze, isLoading }: InputPanelProps) {
	const [imageUrl, setImageUrl] = useState("")
	const [imageFile, setImageFile] = useState("")
	const [movieName, setMovieName] = useState("")
	const [uploadMode, setUploadMode] = useState<"url" | "file">("url")
	const [preview, setPreview] = useState<string | null>(null)

	const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const url = e.target.value
		setImageUrl(url)
		if (url) setPreview(url)
	}

	const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0]
		if (file) {
			const reader = new FileReader()
			reader.onload = (event) => {
				const result = event.target?.result as string
				setImageFile(result)
				setPreview(result)
			}
			reader.readAsDataURL(file)
		}
	}

	const handleAnalyze = () => {
		if (uploadMode === "url" && imageUrl && movieName) {
			onAnalyze(imageUrl, movieName, false)
		} else if (uploadMode === "file" && imageFile && movieName) {
			onAnalyze(imageFile, movieName, true)
		}
	}

	const canSubmit = movieName && (uploadMode === "url" ? imageUrl : imageFile)

	return (
		<div className="flex flex-col h-full">
			{/* Header */}
			<div className="px-5 pt-6 pb-4">
				<div className="flex items-center gap-2.5 mb-1">
					<Clapperboard className="w-5 h-5 text-accent" />
					<h1 className="text-xl font-bold tracking-tight">CineLens AI</h1>
				</div>
				<p className="text-xs text-muted-foreground">Identify actors and analyze movie scenes</p>
			</div>

			{/* Form */}
			<div className="flex-1 px-5 space-y-5 overflow-y-auto pb-4">
				{/* Movie Name */}
				<div className="space-y-1.5">
					<label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
						Movie name
					</label>
					<Input
						type="text"
						placeholder="Inception, The Dark Knight..."
						value={movieName}
						onChange={(e) => setMovieName(e.target.value)}
					/>
				</div>

				{/* Mode Toggle */}
				<div className="space-y-1.5">
					<label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
						Frame source
					</label>
					<div className="grid grid-cols-2 gap-1.5 p-1 bg-secondary rounded-lg">
						{(["url", "file"] as const).map((mode) => (
							<button
								key={mode}
								onClick={() => setUploadMode(mode)}
								className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-medium transition-all ${uploadMode === mode
									? "bg-background text-foreground shadow-sm"
									: "text-muted-foreground hover:text-foreground"
									}`}
							>
								{mode === "url" ? <Link2 className="w-3.5 h-3.5" /> : <Upload className="w-3.5 h-3.5" />}
								{mode === "url" ? "URL" : "Upload"}
							</button>
						))}
					</div>
				</div>

				{/* Input */}
				{uploadMode === "url" ? (
					<div className="space-y-1.5">
						<label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
							Image URL
						</label>
						<Input
							type="url"
							placeholder="https://..."
							value={imageUrl}
							onChange={handleUrlChange}
						/>
					</div>
				) : (
					<label className="block cursor-pointer">
						<div className="border border-dashed border-border hover:border-accent/50 rounded-lg p-6 text-center transition-colors">
							<Upload className="w-6 h-6 mx-auto mb-2 text-muted-foreground" />
							<p className="text-sm text-foreground font-medium">Choose file</p>
							<p className="text-xs text-muted-foreground mt-0.5">JPG, PNG up to 10MB</p>
						</div>
						<input type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
					</label>
				)}

				{/* Preview */}
				{preview && (
					<div className="space-y-1.5">
						<label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
							Preview
						</label>
						<div className="overflow-hidden rounded-lg border border-border">
							<img
								src={preview}
								alt="Preview"
								referrerPolicy="no-referrer"
								className="w-full h-48 object-cover"
								onError={() => setPreview(null)}
							/>
						</div>
					</div>
				)}

				{/* How it works — compact */}
				{!preview && (
					<div className="rounded-lg bg-secondary/50 p-3.5">
						<p className="text-xs font-medium text-foreground mb-2">How it works</p>
						<ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
							<li>Enter a movie name and frame</li>
							<li>AI detects and identifies all actors</li>
							<li>Get detailed scene analysis</li>
						</ol>
					</div>
				)}
			</div>

			{/* Submit */}
			<div className="p-5 border-t border-border">
				<Button
					onClick={handleAnalyze}
					disabled={!canSubmit || isLoading}
					className="w-full h-10"
				>
					{isLoading ? (
						<>
							<span className="animate-spin mr-1.5">⏳</span>
							Analyzing...
						</>
					) : (
						<>
							<Film className="w-4 h-4 mr-1.5" />
							Analyze Frame
						</>
					)}
				</Button>
			</div>
		</div>
	)
}
