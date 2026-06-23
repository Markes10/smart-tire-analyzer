"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { HealthScoreRing } from "@/components/health-score-ring"
import { WearPatternVisual } from "@/components/wear-pattern-visual"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { getAnalysisBySession, type AnalysisResult } from "@/lib/analyze"
import {
  AlertTriangle,
  ArrowLeft,
  Brain,
  Calendar,
  CheckCircle2,
  Clock,
  Cloud,
  Cpu,
  Download,
  Gauge,
  Info,
  MapPin,
  Network,
  Navigation,
  RadioTower,
  Ruler,
  Shield,
  TrendingDown,
} from "lucide-react"

type VisualPattern = "even" | "center" | "edge" | "side-wall" | "one-side" | "cupping" | "feathering" | "patch"

type SidewallRow = {
  key: string
  label: string
  value: string
}

const sidewallFields = [
  ["brand", "Brand"],
  ["tire_model", "Model"],
  ["tire_size", "Size"],
  ["dot_code", "DOT"],
  ["load_index", "Load index"],
  ["speed_rating", "Speed rating"],
  ["extraction_confidence", "Confidence"],
] as const

function riskBadgeVariant(risk: string) {
  if (risk === "HIGH" || risk === "CRITICAL") return "destructive"
  if (risk === "MODERATE") return "secondary"
  return "default"
}

function patternForVisual(label?: string): VisualPattern {
  switch (label) {
    case "center_wear":
      return "center"
    case "edge_wear":
      return "edge"
    case "side_wall_wear":
      return "side-wall"
    case "one_side_wear":
      return "one-side"
    case "cupping_wear":
      return "cupping"
    case "feathering_wear":
      return "feathering"
    case "patchy_wear":
      return "patch"
    default:
      return "even"
  }
}

function healthScorePercent(score: number | undefined): number {
  const value = Number(score ?? 0)
  return Math.round(value <= 10 ? value * 10 : value)
}

function wearLevelsFromDepths(result: AnalysisResult): number[] {
  const tread = result.predictions.tread_depths_mm
  const values = [tread.tread_1, tread.tread_2, tread.tread_3, tread.tread_4]
  const levels = values.map((depth) => Math.max(0, Math.min(100, Math.round((depth / 12) * 100))))
  return [levels[0], levels[1], Math.round((levels[1] + levels[2]) / 2), levels[2], levels[3]]
}

function formatKm(value?: number): string {
  if (value == null) return "Unknown"
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K km`
  return `${Math.round(value)} km`
}

function formatSidewallValue(sidewall: Record<string, any>, key: string): string | null {
  const value = sidewall[key]
  if (value == null || value === "") return null

  if (key === "tire_size" && typeof value === "object") {
    return value.full_formatted ?? value.raw ?? null
  }

  if (key === "dot_code" && typeof value === "object") {
    return value.full ?? value.manufacture_date_text ?? null
  }

  if (Array.isArray(value)) return value.length ? value.join(", ") : null
  if (typeof value === "object") return null
  return String(value)
}

function formatSidewallSource(sidewall: Record<string, any>): string {
  switch (sidewall.source) {
    case "gemini_vision":
      return "Gemini Vision"
    case "unavailable":
      return "Gemini unavailable"
    case "error":
      return "Extraction issue"
    default:
      return sidewall.source ? String(sidewall.source) : "Sidewall scan"
  }
}

function buildSidewallRows(sidewall?: Record<string, any>): SidewallRow[] {
  if (!sidewall) return []

  return sidewallFields.flatMap(([key, label]) => {
    const value = formatSidewallValue(sidewall, key)
    return value ? [{ key, label, value }] : []
  })
}

function resultsSidebar({
  result,
  score,
  tread,
  sidewall,
  sidewallRows,
}: {
  result: AnalysisResult
  score: number
  tread: AnalysisResult["predictions"]["tread_depths_mm"]
  sidewall?: Record<string, any>
  sidewallRows: SidewallRow[]
}) {
  return (
    <div className="space-y-6">
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Gauge className="h-5 w-5 text-primary" />
            Overall Health
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center py-6">
          <HealthScoreRing score={score} />
          <Badge className="mt-4" variant={riskBadgeVariant(result.risk_level)}>
            {result.risk_level} Risk
          </Badge>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Ruler className="h-5 w-5 text-primary" />
            Tread Depth
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-foreground">{tread.average}</span>
            <span className="text-xl text-muted-foreground">mm</span>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Minimum Safe</span>
              <span className="text-foreground">1.6mm</span>
            </div>
            <Progress value={(tread.average / 12) * 100} className="h-2" />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Detected Range</span>
              <span className="text-foreground">
                {tread.min}mm - {tread.max}mm
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingDown className="h-5 w-5 text-primary" />
            Remaining Life
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-foreground">
            {formatKm(result.predictions.remaining_life_km)}
          </div>
          <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
            <Shield className="h-4 w-4" />
            {Math.round(result.confidence * 100)}% confidence
          </div>
        </CardContent>
      </Card>

      {sidewall && (
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-lg">Sidewall Details</CardTitle>
              <Badge variant={sidewall.source === "gemini_vision" ? "default" : "secondary"}>
                {formatSidewallSource(sidewall)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {sidewallRows.length > 0 ? (
              <div className="grid gap-3">
                {sidewallRows.map((row) => (
                  <div key={row.key} className="flex justify-between gap-4">
                    <span className="text-muted-foreground">{row.label}</span>
                    <span className="text-right font-medium text-foreground">{row.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-md border border-border/50 bg-muted/30 p-3 text-muted-foreground">
                No readable tire markings were returned from the sidewall image.
              </div>
            )}
            {sidewall.extraction_notes && (
              <div className="rounded-md border border-border/50 bg-muted/30 p-3 text-muted-foreground">
                {String(sidewall.extraction_notes)}
              </div>
            )}
            {sidewall.all_visible_text && (
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="mb-1 text-xs text-muted-foreground">Visible text</div>
                <div className="break-words text-foreground">
                  {String(sidewall.all_visible_text)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function resultsDetails({
  result,
  pattern,
  wearLevels,
  enterprise,
}: {
  result: AnalysisResult
  pattern: VisualPattern
  wearLevels: number[]
  enterprise?: Record<string, any>
}) {
  return (
    <div className="space-y-6 lg:col-span-2">
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Gauge className="h-5 w-5 text-primary" />
            Wear Pattern Analysis
          </CardTitle>
          <CardDescription>
            {result.predictions.wear_pattern.label_display ?? result.predictions.wear_pattern.label}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <WearPatternVisual pattern={pattern} wearLevels={wearLevels} />
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Info className="h-5 w-5 text-primary" />
            Driving Context
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="flex items-center gap-3">
              <Cloud className="h-5 w-5 text-primary" />
              <div>
                <div className="text-sm font-medium text-foreground">Weather</div>
                <div className="text-sm text-muted-foreground">
                  {result.context?.weather_condition ?? "Not provided"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-primary" />
              <div>
                <div className="text-sm font-medium text-foreground">Road</div>
                <div className="text-sm text-muted-foreground">
                  {result.context?.road_condition ?? "Not provided"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <MapPin className="h-5 w-5 text-primary" />
              <div>
                <div className="text-sm font-medium text-foreground">Terrain</div>
                <div className="text-sm text-muted-foreground">
                  {result.context?.terrain_type ?? "Not provided"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Navigation className="h-5 w-5 text-primary" />
              <div>
                <div className="text-sm font-medium text-foreground">Route</div>
                <div className="text-sm text-muted-foreground">
                  {result.context?.route_distance_km != null ? `${result.context.route_distance_km} km` : "Not provided"}
                </div>
              </div>
            </div>
          </div>
          {(result.context?.street_view_visual_summary || result.context?.road_condition_basis) && (
            <div className="mt-4 rounded-md border border-border/50 bg-muted/40 p-3 text-sm text-muted-foreground">
              {result.context?.street_view_visual_summary ?? result.context?.road_condition_basis}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            Recommendation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {result.reasoning?.driving_advice ?? result.predictions.wear_pattern.advice ?? "Continue monitoring this tire regularly."}
          </p>
          {result.alerts.length > 0 && (
            <div className="space-y-3">
              {result.alerts.map((alert, index) => (
                <div key={`${alert.message}-${index}`} className="flex gap-3 text-sm">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                  <span className="text-muted-foreground">{alert.message}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {enterprise && (
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Brain className="h-5 w-5 text-primary" />
              Enterprise AI Layer
            </CardTitle>
            <CardDescription>MLOps, edge AI, XAI, IoT, digital twin, agents, and RAG outputs</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">Confidence</div>
                <div className="mt-1 text-xl font-semibold text-foreground">
                  {enterprise.confidence_estimation?.prediction_confidence_pct ?? "--"}%
                </div>
              </div>
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">Failure Risk</div>
                <div className="mt-1 text-xl font-semibold text-foreground">
                  {enterprise.confidence_estimation?.failure_risk_label ?? "--"}
                </div>
              </div>
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">RUL</div>
                <div className="mt-1 text-xl font-semibold text-foreground">
                  {formatKm(enterprise.predictive_maintenance?.remaining_useful_life_km)}
                </div>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-md border border-border/50 bg-muted/30 p-4">
                <div className="mb-3 flex items-center gap-2 font-medium text-foreground">
                  <Cpu className="h-4 w-4 text-primary" />
                  Edge + Digital Twin
                </div>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>Offline: {enterprise.edge_ai?.offline_prediction_mode ? "Ready" : "Unavailable"}</div>
                  <div>Stage: {enterprise.digital_twin?.virtual_ai_simulation?.lifecycle_stage ?? "Unknown"}</div>
                  <div>Forecast: {enterprise.predictive_maintenance?.failure_forecast_window ?? "Unknown"}</div>
                </div>
              </div>

              <div className="rounded-md border border-border/50 bg-muted/30 p-4">
                <div className="mb-3 flex items-center gap-2 font-medium text-foreground">
                  <RadioTower className="h-4 w-4 text-primary" />
                  IoT Fusion
                </div>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>
                    Channels: {(enterprise.iot_sensor_fusion?.active_sensor_channels ?? []).join(", ") || "Image only"}
                  </div>
                  <div>
                    Alerts: {(enterprise.iot_sensor_fusion?.sensor_alerts ?? []).join(", ") || "None"}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-md border border-border/50 bg-muted/30 p-4">
              <div className="mb-3 flex items-center gap-2 font-medium text-foreground">
                <Network className="h-4 w-4 text-primary" />
                XAI Highlights
              </div>
              <div className="flex flex-wrap gap-2">
                {(enterprise.explainable_ai?.damaged_region_highlights ?? []).map((region: any) => (
                  <Badge key={region.label} variant="outline">
                    {region.label}: {Math.round((region.intensity ?? 0) * 100)}%
                  </Badge>
                ))}
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {enterprise.explainable_ai?.why_classified_as_damaged}
              </p>
            </div>

            <div className="rounded-md border border-border/50 bg-muted/30 p-4">
              <div className="mb-3 font-medium text-foreground">Autonomous Agents</div>
              <div className="grid gap-2 text-sm text-muted-foreground">
                {(enterprise.multi_agent_ai?.agents ?? []).map((agent: any) => (
                  <div key={agent.agent} className="flex gap-2">
                    <span className="min-w-0 flex-1 font-medium text-foreground">{agent.agent}</span>
                    <span className="min-w-0 flex-[1.5]">{agent.output}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/50 bg-card/30 px-4 py-3 text-sm text-muted-foreground">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-1.5">
            <Calendar className="h-4 w-4" />
            {new Date(result.timestamp).toLocaleDateString()}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            {new Date(result.timestamp).toLocaleTimeString()}
          </span>
          {result.model_version && (
            <span className="flex items-center gap-1.5">
              <Shield className="h-4 w-4" />
              {result.model_version}
            </span>
          )}
        </div>
        <Badge variant="outline">ID: {result.session_id}</Badge>
      </div>
    </div>
  )
}

type ResultState = {
  result: AnalysisResult | null
  isLoading: boolean
  error: string | null
  sessionId: string | null
}

function readInitialResultState(): ResultState {
  if (typeof window === "undefined") {
    return { result: null, isLoading: true, error: null, sessionId: null }
  }

  try {
    const params = new URLSearchParams(window.location.search)
    const sessionId = params.get("id")
    const stored = sessionId
      ? sessionStorage.getItem(`smart-tire:v1:analysis:${sessionId}`) ?? sessionStorage.getItem(`smart-tire:analysis:${sessionId}`)
      : sessionStorage.getItem("smart-tire:v1:last-analysis") ?? sessionStorage.getItem("smart-tire:last-analysis")

    if (stored) {
      return {
        result: JSON.parse(stored) as AnalysisResult,
        isLoading: false,
        error: null,
        sessionId,
      }
    }

    if (!sessionId) {
      return {
        result: null,
        isLoading: false,
        error: "No analysis result is available yet.",
        sessionId: null,
      }
    }

    return { result: null, isLoading: true, error: null, sessionId }
  } catch (err) {
    return {
      result: null,
      isLoading: false,
      error: err instanceof Error ? err.message : "Could not load analysis result.",
      sessionId: null,
    }
  }
}

export default function ResultsPage() {
  const [state, setState] = useState<ResultState>(readInitialResultState)
  const { result, isLoading, error, sessionId } = state

  useEffect(() => {
    if (!isLoading || !sessionId || result) {
      return
    }

    let mounted = true
    const lookupSessionId = sessionId

    async function loadResult() {
      try {
        const fetched = await getAnalysisBySession(lookupSessionId)
        sessionStorage.setItem(`smart-tire:v1:analysis:${fetched.session_id}`, JSON.stringify(fetched))
        sessionStorage.setItem("smart-tire:v1:last-analysis", JSON.stringify(fetched))
        if (mounted) {
          setState({
            result: fetched,
            isLoading: false,
            error: null,
            sessionId: fetched.session_id,
          })
        }
      } catch (err) {
        if (mounted) {
          setState({
            result: null,
            isLoading: false,
            error: err instanceof Error ? err.message : "Could not load analysis result.",
            sessionId: lookupSessionId,
          })
        }
      }
    }

    loadResult()
    return () => {
      mounted = false
    }
  }, [isLoading, result, sessionId])

  const derived = useMemo(() => {
    if (!result) return null
    const tread = result.predictions.tread_depths_mm
    const score = healthScorePercent(result.predictions.health_score)
    return {
      tread,
      score,
      pattern: patternForVisual(result.predictions.wear_pattern.label),
      wearLevels: wearLevelsFromDepths(result),
      sidewall: (
        result.metadata?.sidewall_details ??
        result.metadata?.sidewall_analysis ??
        (result as any).sidewall_analysis
      ) as Record<string, any> | undefined,
      enterprise: result.enterprise_ai as Record<string, any> | undefined,
    }
  }, [result])

  const downloadReport = () => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `smart-tire-report-${result.session_id}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="flex flex-1 items-center justify-center pt-16">
          <div className="text-sm text-muted-foreground">Loading analysis result&hellip;</div>
        </main>
        <Footer />
      </div>
    )
  }

  if (error || !result || !derived) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="flex flex-1 items-center justify-center px-4 pt-16">
          <Card className="max-w-md border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle>No Result Found</CardTitle>
              <CardDescription>{error ?? "Run a tire analysis first."}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/analyze">Start Analysis</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
        <Footer />
      </div>
    )
  }

  const sidewallRows = buildSidewallRows(derived.sidewall)

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <Button variant="ghost" size="sm" className="mb-2 -ml-2 gap-1" asChild>
                <Link href="/analyze">
                  <ArrowLeft className="h-4 w-4" />
                  Back to Analysis
                </Link>
              </Button>
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Analysis Results
              </h1>
              <p className="mt-1 text-muted-foreground">{result.status}</p>
            </div>
            <Button size="sm" className="gap-1.5" onClick={downloadReport}>
              <Download className="h-4 w-4" />
              Download Report
            </Button>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {resultsSidebar({
              result,
              score: derived.score,
              tread: derived.tread,
              sidewall: derived.sidewall,
              sidewallRows,
            })}
            {resultsDetails({
              result,
              pattern: derived.pattern,
              wearLevels: derived.wearLevels,
              enterprise: derived.enterprise,
            })}
          </div>

          <Separator className="my-8" />
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Button size="lg" asChild>
              <Link href="/analyze">Analyze Another Tire</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/history">View Analysis History</Link>
            </Button>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
