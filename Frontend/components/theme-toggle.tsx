"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "./theme-provider"
import { useEffect, useState } from "react"

export function ThemeToggle() {
	const { theme, toggleTheme } = useTheme()
	const [mounted, setMounted] = useState(false)

	useEffect(() => {
		setMounted(true)
	}, [])

	if (!mounted) {
		return (
			<div className="p-2 rounded-lg bg-card border border-border w-9 h-9" />
		)
	}

	return (
		<button
			onClick={toggleTheme}
			className="p-2 rounded-lg bg-card border border-border hover:bg-accent/10 transition-colors"
			aria-label="Toggle theme"
		>
			{theme === "dark" ? (
				<Sun className="w-5 h-5 text-accent" />
			) : (
				<Moon className="w-5 h-5 text-accent" />
			)}
		</button>
	)
}
