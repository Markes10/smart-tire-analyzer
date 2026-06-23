"use client"

import { type ComponentType, useReducer } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { ImageUpload } from "@/components/image-upload"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { analyzeImage, analyzeRouteRoadCondition, type RouteRoadConditionResult } from "@/lib/analyze"
import dynamic from "next/dynamic"
import {
  Gauge,
  ArrowRight,
  Info,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Zap,
  RotateCcw,
  Map as MapIcon,
  Route as RouteIcon,
  Eye,
  RadioTower,
  Thermometer,
} from "lucide-react"
import { useRouter } from "next/navigation"

interface TireImage {
  file: File | null
  preview: string | null
}

interface RouteInfo {
  source: string
  destination: string
}

interface TelemetryInfo {
  tirePressurePsi: string
  temperatureC: string
  vibrationG: string
  speedKmph: string
}

function parseCoordinatePair(value: string): { latitude: number; longitude: number } | null {
  const [latText, lonText] = value.split(",").map((part) => part.trim())
  const latitude = Number(latText)
  const longitude = Number(lonText)

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return { latitude, longitude }
}

function parseOptionalNumber(value: string): number | undefined {
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : undefined
}

const RouteMapSelector = dynamic(
  () => import("@/components/route-map-selector").then((mod) => mod.RouteMapSelector),
  {
    ssr: false,
    loading: () => (
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapIcon className="h-5 w-5 text-primary" />
            Route Selection Map
          </CardTitle>
          <CardDescription>Select source and destination on the map</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-96 items-center justify-center rounded-lg bg-muted">
            Loading map&hellip;
          </div>
        </CardContent>
      </Card>
    ),
  }
)

type AnalyzeState = {
  analysisMode: "quick" | "full"
  isAnalyzing: boolean
  progress: number
  error: string | null
  route: RouteInfo
  routeCondition: RouteRoadConditionResult | null
  isCheckingRoute: boolean
  routeError: string | null
  telemetry: TelemetryInfo
  frontView: TireImage
  sideView: TireImage
  closeupView: TireImage
}

type AnalyzeAction =
  | { type: "setAnalysisMode"; value: "quick" | "full" }
  | { type: "setRoute"; source: string; destination: string }
  | { type: "routeCheckStarted" }
  | { type: "routeCheckSucceeded"; result: RouteRoadConditionResult }
  | { type: "routeCheckFailed"; message: string }
  | { type: "setTelemetry"; field: keyof TelemetryInfo; value: string }
  | { type: "setImage"; slot: "frontView" | "sideView" | "closeupView"; value: TireImage }
  | { type: "analysisStarted" }
  | { type: "analysisProgressTick" }
  | { type: "analysisSucceeded" }
  | { type: "analysisFailed"; message: string }
  | { type: "reset" }

const emptyTireImage: TireImage = { file: null, preview: null }
const emptyTelemetry: TelemetryInfo = {
  tirePressurePsi: "",
  temperatureC: "",
  vibrationG: "",
  speedKmph: "",
}

const initialAnalyzeState: AnalyzeState = {
  analysisMode: "quick",
  isAnalyzing: false,
  progress: 0,
  error: null,
  route: { source: "", destination: "" },
  routeCondition: null,
  isCheckingRoute: false,
  routeError: null,
  telemetry: emptyTelemetry,
  frontView: emptyTireImage,
  sideView: emptyTireImage,
  closeupView: emptyTireImage,
}

function analyzeReducer(state: AnalyzeState, action: AnalyzeAction): AnalyzeState {
  switch (action.type) {
    case "setAnalysisMode":
      return { ...state, analysisMode: action.value }
    case "setRoute":
      return {
        ...state,
        route: { source: action.source, destination: action.destination },
        routeCondition: null,
        routeError: null,
      }
    case "routeCheckStarted":
      return { ...state, isCheckingRoute: true, routeError: null }
    case "routeCheckSucceeded":
      return { ...state, isCheckingRoute: false, routeCondition: action.result }
    case "routeCheckFailed":
      return { ...state, isCheckingRoute: false, routeError: action.message }
    case "setTelemetry":
      return {
        ...state,
        telemetry: { ...state.telemetry, [action.field]: action.value },
      }
    case "setImage":
      return { ...state, [action.slot]: action.value }
    case "analysisStarted":
      return { ...state, isAnalyzing: true, error: null, progress: 0 }
    case "analysisProgressTick":
      return { ...state, progress: state.progress >= 90 ? state.progress : state.progress + 10 }
    case "analysisSucceeded":
      return { ...state, isAnalyzing: false, progress: 100 }
    case "analysisFailed":
      return { ...state, isAnalyzing: false, error: action.message, progress: 0 }
    case "reset":
      return initialAnalyzeState
    default:
      return state
  }
}

function conditionBadgeVariant(condition?: string) {
  if (condition === "poor") return "destructive"
  if (condition === "fair") return "secondary"
  return "default"
}

function formatRoadCondition(condition?: string): string {
  if (!condition) return "Unknown"
  return condition.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function RouteRoadConditionCard({
  canCheck,
  isChecking,
  result,
  error,
  onCheck,
}: {
  canCheck: boolean
  isChecking: boolean
  result: RouteRoadConditionResult | null
  error: string | null
  onCheck: () => void
}) {
  const covered = result?.street_view_covered_samples ?? 0
  const total = result?.street_view_sample_count ?? 0
  const samples = result?.street_view_samples?.slice(0, 4) ?? []

  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RouteIcon className="h-5 w-5 text-primary" />
          Route Road Condition
        </CardTitle>
        <CardDescription>Street View road-surface and terrain context for the selected route</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-muted-foreground">
            {result
              ? result.street_view_visual_summary ?? result.road_condition_basis
              : "Select both route points to check road condition before analysis."}
          </div>
          <Button
            type="button"
            variant="outline"
            className="shrink-0 gap-2"
            disabled={!canCheck || isChecking}
            onClick={onCheck}
          >
            {isChecking ? (
              <RotateCcw className="h-4 w-4 animate-spin" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
            {isChecking ? "Checking..." : "Check Road"}
          </Button>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">Condition</div>
                <Badge className="mt-2" variant={conditionBadgeVariant(result.road_condition)}>
                  {formatRoadCondition(result.road_condition)}
                </Badge>
              </div>
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">Street View</div>
                <div className="mt-2 text-sm font-medium text-foreground">
                  {covered}/{total} samples
                </div>
              </div>
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">Distance</div>
                <div className="mt-2 text-sm font-medium text-foreground">
                  {result.route_distance_km != null ? `${result.route_distance_km} km` : "Unknown"}
                </div>
              </div>
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <div className="text-xs text-muted-foreground">Wear Factor</div>
                <div className="mt-2 text-sm font-medium text-foreground">
                  {result.road_wear_multiplier != null ? `${result.road_wear_multiplier}x` : "Unknown"}
                </div>
              </div>
            </div>

            {result.road_condition_basis && (
              <div className="rounded-md border border-border/50 bg-muted/30 p-3 text-sm text-muted-foreground">
                {result.road_condition_basis}
              </div>
            )}

            {samples.length > 0 && (
              <div className="grid gap-2 sm:grid-cols-2">
                {samples.map((sample, index) => (
                  <div key={`${sample.latitude}-${sample.longitude}-${index}`} className="rounded-md border border-border/50 bg-muted/20 p-3 text-xs">
                    <div className="font-medium text-foreground">Sample {index + 1}</div>
                    <div className="mt-1 text-muted-foreground">
                      Street View: {sample.street_view_status ?? "unknown"}
                    </div>
                    <div className="text-muted-foreground">
                      Surface: {sample.surface_texture ?? "unreadable"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

type RouteMapSelectorProps = RouteInfo & {
  onRouteChange: (source: string, destination: string) => void
}

type AnalyzeUploadTabsProps = {
  analysisMode: "quick" | "full"
  route: RouteInfo
  frontView: TireImage
  sideView: TireImage
  closeupView: TireImage
  hasRoute: boolean
  isCheckingRoute: boolean
  routeCondition: RouteRoadConditionResult | null
  routeError: string | null
  RouteMapSelectorComponent: ComponentType<RouteMapSelectorProps>
  onAnalysisModeChange: (mode: "quick" | "full") => void
  onRouteChange: (source: string, destination: string) => void
  onCheckRoute: () => void
  onFrontViewChange: (file: File | null, preview: string | null) => void
  onSideViewChange: (file: File | null, preview: string | null) => void
  onCloseupViewChange: (file: File | null, preview: string | null) => void
}

function analyzeUploadTabs({
  analysisMode,
  route,
  frontView,
  sideView,
  closeupView,
  hasRoute,
  isCheckingRoute,
  routeCondition,
  routeError,
  RouteMapSelectorComponent,
  onAnalysisModeChange,
  onRouteChange,
  onCheckRoute,
  onFrontViewChange,
  onSideViewChange,
  onCloseupViewChange,
}: AnalyzeUploadTabsProps) {
  const routeTools = (
    <>
      <RouteMapSelectorComponent
        source={route.source}
        destination={route.destination}
        onRouteChange={onRouteChange}
      />
      <RouteRoadConditionCard
        canCheck={hasRoute}
        isChecking={isCheckingRoute}
        result={routeCondition}
        error={routeError}
        onCheck={onCheckRoute}
      />
    </>
  )

  return (
    <Tabs value={analysisMode} onValueChange={(value) => onAnalysisModeChange(value as "quick" | "full")} className="mb-8">
      <TabsList className="mx-auto grid w-full max-w-md grid-cols-2">
        <TabsTrigger value="quick" className="gap-2">
          <Zap className="h-4 w-4" />
          Quick Scan
        </TabsTrigger>
        <TabsTrigger value="full" className="gap-2">
          <Gauge className="h-4 w-4" />
          Full Analysis
        </TabsTrigger>
      </TabsList>

      <TabsContent value="quick" className="mt-8 space-y-6">
        {routeTools}
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-primary" />
              Quick Scan
            </CardTitle>
            <CardDescription>
              Upload a single front-view image for instant health assessment
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ImageUpload
              label="Front View"
              description="Capture the tire tread pattern clearly"
              value={frontView.preview}
              onChange={onFrontViewChange}
            />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="full" className="mt-8 space-y-6">
        {routeTools}
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5 text-primary" />
              Full Analysis
            </CardTitle>
            <CardDescription>
              Upload multiple views for comprehensive tire assessment
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-3">
              <ImageUpload
                label="Front View"
                description="Tread pattern"
                value={frontView.preview}
                onChange={onFrontViewChange}
              />
              <ImageUpload
                label="Side View"
                description="Sidewall condition"
                value={sideView.preview}
                onChange={onSideViewChange}
              />
              <ImageUpload
                label="Closeup"
                description="Wear details"
                value={closeupView.preview}
                onChange={onCloseupViewChange}
              />
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}

function analysisProgressCard({ progress }: { progress: number }) {
  return (
    <Card className="mb-8 border-primary/50 bg-primary/5">
      <CardContent className="py-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
            <span className="text-sm font-medium text-foreground">
              Analyzing tire condition&hellip;
            </span>
          </div>
          <span className="text-sm text-muted-foreground">
            {Math.round(progress)}%
          </span>
        </div>
        <Progress value={progress} className="h-2" />
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-muted-foreground sm:grid-cols-4">
          <div className={progress > 20 ? "text-primary" : ""}>
            Preprocessing&hellip;
          </div>
          <div className={progress > 40 ? "text-primary" : ""}>
            Feature extraction&hellip;
          </div>
          <div className={progress > 70 ? "text-primary" : ""}>
            AI analysis&hellip;
          </div>
          <div className={progress > 90 ? "text-primary" : ""}>
            Generating report&hellip;
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function AnalyzePage() {
  const { push } = useRouter()
  const [state, dispatch] = useReducer(analyzeReducer, initialAnalyzeState)
  const {
    analysisMode,
    isAnalyzing,
    progress,
    error,
    route,
    routeCondition,
    isCheckingRoute,
    routeError,
    telemetry,
    frontView,
    sideView,
    closeupView,
  } = state

  const primaryImage = frontView.file ?? closeupView.file
  const hasImages = primaryImage !== null
  const sourceCoordinates = parseCoordinatePair(route.source)
  const destinationCoordinates = parseCoordinatePair(route.destination)
  const hasRoute = sourceCoordinates !== null && destinationCoordinates !== null

  const handleRouteChange = (source: string, destination: string) => {
    dispatch({ type: "setRoute", source, destination })
  }

  const handleCheckRoute = async () => {
    if (!sourceCoordinates || !destinationCoordinates) {
      dispatch({ type: "routeCheckFailed", message: "Select both source and destination points on the map." })
      return
    }

    dispatch({ type: "routeCheckStarted" })

    try {
      const result = await analyzeRouteRoadCondition({
        sourceLatitude: sourceCoordinates.latitude,
        sourceLongitude: sourceCoordinates.longitude,
        destinationLatitude: destinationCoordinates.latitude,
        destinationLongitude: destinationCoordinates.longitude,
      })
      dispatch({ type: "routeCheckSucceeded", result })
    } catch (err) {
      dispatch({
        type: "routeCheckFailed",
        message: err instanceof Error ? err.message : "Road condition check failed.",
      })
    }
  }

  const handleAnalyze = async () => {
    if (!primaryImage) {
      dispatch({
        type: "analysisFailed",
        message: "Upload a front-view or closeup tread image before starting analysis.",
      })
      return
    }

    dispatch({ type: "analysisStarted" })

    const interval = setInterval(() => {
      dispatch({ type: "analysisProgressTick" })
    }, 350)

    try {
      const coordinates = sourceCoordinates ?? destinationCoordinates
      const result = await analyzeImage({
        imageUri: primaryImage,
        sidewallImage: sideView.file,
        latitude: coordinates?.latitude,
        longitude: coordinates?.longitude,
        sourceLatitude: sourceCoordinates?.latitude,
        sourceLongitude: sourceCoordinates?.longitude,
        destinationLatitude: destinationCoordinates?.latitude,
        destinationLongitude: destinationCoordinates?.longitude,
        tirePressurePsi: parseOptionalNumber(telemetry.tirePressurePsi),
        temperatureC: parseOptionalNumber(telemetry.temperatureC),
        vibrationG: parseOptionalNumber(telemetry.vibrationG),
        speedKmph: parseOptionalNumber(telemetry.speedKmph),
        context: routeCondition ? { route_precheck_available: true, ...routeCondition } : undefined,
      })

      sessionStorage.setItem("smart-tire:v1:last-analysis", JSON.stringify(result))
      sessionStorage.setItem(`smart-tire:v1:analysis:${result.session_id}`, JSON.stringify(result))
      dispatch({ type: "analysisSucceeded" })
      push(`/analyze/results?id=${encodeURIComponent(result.session_id)}`)
    } catch (err) {
      dispatch({
        type: "analysisFailed",
        message: err instanceof Error ? err.message : "Analysis failed. Please try again.",
      })
    } finally {
      clearInterval(interval)
    }
  }

  const handleReset = () => {
    dispatch({ type: "reset" })
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8 text-center">
            <Badge variant="secondary" className="mb-4 gap-1.5">
              <Zap className="h-3 w-3 text-primary" />
              AI Analysis
            </Badge>
            <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Analyze Your Tire
            </h1>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Upload tire images for instant AI-powered health assessment, wear pattern detection, and safety recommendations.
            </p>
          </div>

          {analyzeUploadTabs({
            analysisMode,
            route,
            frontView,
            sideView,
            closeupView,
            hasRoute,
            isCheckingRoute,
            routeCondition,
            routeError,
            RouteMapSelectorComponent: RouteMapSelector,
            onAnalysisModeChange: (value) => dispatch({ type: "setAnalysisMode", value }),
            onRouteChange: handleRouteChange,
            onCheckRoute: handleCheckRoute,
            onFrontViewChange: (file, preview) => dispatch({ type: "setImage", slot: "frontView", value: { file, preview } }),
            onSideViewChange: (file, preview) => dispatch({ type: "setImage", slot: "sideView", value: { file, preview } }),
            onCloseupViewChange: (file, preview) => dispatch({ type: "setImage", slot: "closeupView", value: { file, preview } }),
          })}

          <Card className="mb-8 border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <RadioTower className="h-5 w-5 text-primary" />
                IoT Sensor Fusion
              </CardTitle>
              <CardDescription>Optional telemetry for multimodal tire intelligence</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-2">
                  <Label htmlFor="pressure">Pressure (psi)</Label>
                  <Input
                    id="pressure"
                    inputMode="decimal"
                    placeholder="32"
                    value={telemetry.tirePressurePsi}
                    onChange={(event) => dispatch({ type: "setTelemetry", field: "tirePressurePsi", value: event.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="temperature" className="gap-1.5">
                    <Thermometer className="h-4 w-4 text-primary" />
                    Temperature (C)
                  </Label>
                  <Input
                    id="temperature"
                    inputMode="decimal"
                    placeholder="42"
                    value={telemetry.temperatureC}
                    onChange={(event) => dispatch({ type: "setTelemetry", field: "temperatureC", value: event.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vibration" className="gap-1.5">
                    <Activity className="h-4 w-4 text-primary" />
                    Vibration (g)
                  </Label>
                  <Input
                    id="vibration"
                    inputMode="decimal"
                    placeholder="0.4"
                    value={telemetry.vibrationG}
                    onChange={(event) => dispatch({ type: "setTelemetry", field: "vibrationG", value: event.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="speed">Speed (km/h)</Label>
                  <Input
                    id="speed"
                    inputMode="decimal"
                    placeholder="80"
                    value={telemetry.speedKmph}
                    onChange={(event) => dispatch({ type: "setTelemetry", field: "speedKmph", value: event.target.value })}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {isAnalyzing && analysisProgressCard({ progress })}

          {error && (
            <Card className="mb-8 border-destructive/50 bg-destructive/5">
              <CardContent className="flex items-start gap-3 py-4 text-sm text-destructive">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </CardContent>
            </Card>
          )}

          {/* Tips Card */}
          <Card className="mb-8 border-border/50 bg-card/50">
            <CardContent className="flex items-start gap-4 py-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Info className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h4 className="font-medium text-foreground">Tips for best results</h4>
                <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                  <li>Ensure good lighting - natural daylight works best</li>
                  <li>Capture the full tread width in frame</li>
                  <li>Clean the tire surface if heavily soiled</li>
                  <li>Keep the camera parallel to the tire surface</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Button
              size="lg"
              className="w-full gap-2 sm:w-auto"
              disabled={!hasImages || isAnalyzing}
              onClick={handleAnalyze}
            >
              {isAnalyzing ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  Analyzing&hellip;
                </>
              ) : (
                <>
                  Start Analysis
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
            {hasImages && !isAnalyzing && (
              <Button
                size="lg"
                variant="outline"
                className="w-full gap-2 sm:w-auto"
                onClick={handleReset}
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>
            )}
          </div>

          {/* Analysis Warning */}
          {!hasImages && (
            <div className="mt-8 flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <AlertTriangle className="h-4 w-4" />
              Upload a front-view or closeup tread image to start analysis
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}
