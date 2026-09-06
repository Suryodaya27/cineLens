"use client"

import { useState, useEffect, useCallback, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import InputPanel from "@/components/input-panel"
import OutputPanel from "@/components/output-panel"
import { Loader2, Check, AlertCircle, Circle } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"

interface ProgressStep {
  id: string
  label: string
  status: "pending" | "active" | "done" | "error"
  detail?: string
}

const INITIAL_STEPS: ProgressStep[] = [
  { id: "upload", label: "Uploading image" },
  { id: "download", label: "Downloading image" },
  { id: "init", label: "Loading AI models" },
  { id: "cast", label: "Looking up cast" },
  { id: "detect", label: "Detecting objects" },
  { id: "identify", label: "Identifying actors" },
  { id: "scene", label: "Analyzing scene" },
  { id: "objects", label: "Analyzing objects" },
  { id: "upload_crops", label: "Uploading crops" },
].map((s) => ({ ...s, status: "pending" as const }))

function parseSSE(text: string): Array<{ event: string; data: string }> {
  const events: Array<{ event: string; data: string }> = []
  for (const block of text.split("\n\n").filter(Boolean)) {
    let event = "message"
    let data = ""
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7)
      else if (line.startsWith("data: ")) data = line.slice(6)
    }
    if (data) events.push({ event, data })
  }
  return events
}

const STEP_MAP: Record<string, string> = {
  download: "download", init: "init", cast: "cast", detect: "detect",
  identify: "identify", scene: "scene", objects: "objects", upload: "upload_crops",
}

function HomeContent() {
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [hideInputPanel, setHideInputPanel] = useState(false)
  const [steps, setSteps] = useState<ProgressStep[]>(INITIAL_STEPS)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const searchParams = useSearchParams()

  const updateStep = useCallback(
    (id: string, status: ProgressStep["status"], detail?: string) => {
      setSteps((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status, detail: detail ?? s.detail } : s))
      )
    },
    []
  )

  useEffect(() => {
    const movieName = searchParams.get("movie_name")
    const imgUrl = searchParams.get("img_url")
    if (movieName && imgUrl) {
      setHideInputPanel(true)
      handleAnalyze(imgUrl, movieName, false)
    }
  }, [searchParams])

  const handleAnalyze = async (imageData: string, movieName: string, isFile: boolean) => {
    setIsLoading(true)
    setResults(null)
    setErrorMsg(null)
    setJobId(null)
    setSteps(INITIAL_STEPS.map((s) => ({ ...s, status: "pending", detail: undefined })))
    updateStep("upload", "active", "Uploading to ImageBB...")

    try {
      const response = await fetch("/api/analyze-movie", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          imageUrl: isFile ? undefined : imageData,
          imageFile: isFile ? imageData : undefined,
          movieName,
        }),
      })

      if (!response.ok || !response.body) {
        const err = await response.json().catch(() => ({ error: "Unknown error" }))
        throw new Error(err.error || `Server error ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split("\n\n")
        buffer = parts.pop() || ""

        for (const part of parts) {
          if (!part.trim()) continue
          for (const { event, data } of parseSSE(part + "\n\n")) {
            let payload: Record<string, unknown>
            try { payload = JSON.parse(data) } catch { continue }

            if (event === "imagebb") {
              updateStep("upload", "done", "Uploaded")
              updateStep("download", "active")
            } else if (event === "progress") {
              const uiStep = STEP_MAP[payload.step as string] || (payload.step as string)
              const msg = payload.message as string
              if (payload.job_id && !jobId) setJobId(payload.job_id as string)
              if (payload.done) {
                updateStep(uiStep, "done", msg)
                setSteps((prev) => {
                  const idx = prev.findIndex((s) => s.id === uiStep)
                  const next = prev.find((s, i) => i > idx && s.status === "pending")
                  return next ? prev.map((s) => (s.id === next.id ? { ...s, status: "active" } : s)) : prev
                })
              } else {
                setSteps((prev) => {
                  const currentActive = prev.find((s) => s.status === "active")
                  if (!currentActive || currentActive.id === uiStep) {
                    return prev.map((s) => (s.id === uiStep ? { ...s, status: "active", detail: msg } : s))
                  }
                  return prev.map((s) => (s.id === uiStep ? { ...s, detail: msg } : s))
                })
              }
            } else if (event === "complete") {
              const resultData = payload.data as Record<string, unknown>
              if (payload.job_id) setJobId(payload.job_id as string)
              setSteps((prev) => prev.map((s) => ({ ...s, status: "done" as const })))
              if (resultData) {
                setResults({ data: resultData, job_id: payload.job_id } as never)
              }
            } else if (event === "error") {
              setErrorMsg(payload.message as string)
              setSteps((prev) => prev.map((s) => (s.status === "active" ? { ...s, status: "error" as const } : s)))
            }
          }
        }
      }
    } catch (error) {
      console.error("Error analyzing movie frame:", error)
      setErrorMsg(error instanceof Error ? error.message : "Failed to process image")
    } finally {
      setIsLoading(false)
    }
  }

  const activeStep = steps.find((s) => s.status === "active")
  const doneCount = steps.filter((s) => s.status === "done").length
  const progress = (doneCount / steps.length) * 100

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Input Panel */}
      {!hideInputPanel && (
        <div className="border-r border-border overflow-hidden w-full lg:w-[360px] lg:shrink-0 h-screen sticky top-0">
          <InputPanel onAnalyze={handleAnalyze} isLoading={isLoading} />
        </div>
      )}

      {/* Output Panel */}
      <div className="hidden lg:flex flex-1 flex-col overflow-y-auto">
        {isLoading || (errorMsg && !results) ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="w-full max-w-sm px-6 space-y-6">
              {/* Overall progress */}
              <div className="space-y-2 text-center">
                <p className="text-sm font-medium">
                  {activeStep?.detail || activeStep?.label || "Starting..."}
                </p>
                <div className="h-1 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">{doneCount}/{steps.length} steps</p>
                {jobId && (
                  <p className="text-[10px] text-muted-foreground/60 font-mono">Job: {jobId}</p>
                )}
              </div>

              {/* Step list */}
              <div className="space-y-1">
                {steps.map((step) => (
                  <div
                    key={step.id}
                    className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md transition-colors ${step.status === "active" ? "bg-accent/8" : ""
                      }`}
                  >
                    <div className="shrink-0">
                      {step.status === "done" ? (
                        <Check className="w-3.5 h-3.5 text-green-500" />
                      ) : step.status === "active" ? (
                        <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />
                      ) : step.status === "error" ? (
                        <AlertCircle className="w-3.5 h-3.5 text-destructive" />
                      ) : (
                        <Circle className="w-3.5 h-3.5 text-border" />
                      )}
                    </div>
                    <span className={`text-xs ${step.status === "pending" ? "text-muted-foreground/40"
                      : step.status === "error" ? "text-destructive"
                        : "text-foreground"
                      }`}>
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>

              {errorMsg && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <p className="text-xs text-destructive">{errorMsg}</p>
                </div>
              )}
            </div>
          </div>
        ) : results ? (
          <OutputPanel results={results} />
        ) : (
          <div className="flex-1 flex flex-col">
            <div className="sticky top-0 z-10 px-5 py-3 border-b border-border flex justify-end">
              <ThemeToggle />
            </div>
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-2">
                <div className="w-12 h-12 mx-auto bg-secondary rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-muted-foreground/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5zm10.5-11.25h.008v.008h-.008v-.008zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0z"
                    />
                  </svg>
                </div>
                <p className="text-sm text-muted-foreground">Upload a movie frame to get started</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mobile Output */}
      {results && (
        <div className="lg:hidden fixed inset-0 bg-background z-50 overflow-y-auto">
          <div className="p-4">
            <button onClick={() => setResults(null)} className="mb-3 text-sm text-muted-foreground hover:text-foreground">
              ← Back
            </button>
            <OutputPanel results={results} />
          </div>
        </div>
      )}
    </div>
  )
}

export default function Home() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>}>
      <HomeContent />
    </Suspense>
  )
}
