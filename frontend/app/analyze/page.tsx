"use client"

import { useState } from "react"
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
import { analyzeImage } from "@/lib/analyze"
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
            Loading map...
          </div>
        </CardContent>
      </Card>
    ),
  }
)

export default function AnalyzePage() {
  const router = useRouter()
  const [analysisMode, setAnalysisMode] = useState<"quick" | "full">("quick")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [route, setRoute] = useState<RouteInfo>({ source: "", destination: "" })
  const [telemetry, setTelemetry] = useState<TelemetryInfo>({
    tirePressurePsi: "",
    temperatureC: "",
    vibrationG: "",
    speedKmph: "",
  })

  const [frontView, setFrontView] = useState<TireImage>({ file: null, preview: null })
  const [sideView, setSideView] = useState<TireImage>({ file: null, preview: null })
  const [closeupView, setCloseupView] = useState<TireImage>({ file: null, preview: null })

  const primaryImage = frontView.file ?? closeupView.file
  const hasImages = primaryImage !== null

  const handleAnalyze = async () => {
    if (!primaryImage) {
      setError("Upload a front-view or closeup tread image before starting analysis.")
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setProgress(0)

    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return prev
        return prev + 10
      })
    }, 350)

    try {
      const sourceCoordinates = parseCoordinatePair(route.source)
      const destinationCoordinates = parseCoordinatePair(route.destination)
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
      })

      sessionStorage.setItem("smart-tire:last-analysis", JSON.stringify(result))
      sessionStorage.setItem(`smart-tire:analysis:${result.session_id}`, JSON.stringify(result))
      setProgress(100)
      router.push(`/analyze/results?id=${encodeURIComponent(result.session_id)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.")
      setProgress(0)
    } finally {
      clearInterval(interval)
      setIsAnalyzing(false)
    }
  }

  const handleReset = () => {
    setFrontView({ file: null, preview: null })
    setSideView({ file: null, preview: null })
    setCloseupView({ file: null, preview: null })
    setRoute({ source: "", destination: "" })
    setTelemetry({ tirePressurePsi: "", temperatureC: "", vibrationG: "", speedKmph: "" })
    setProgress(0)
    setError(null)
    setIsAnalyzing(false)
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

          {/* Analysis Mode Tabs */}
          <Tabs value={analysisMode} onValueChange={(v) => setAnalysisMode(v as "quick" | "full")} className="mb-8">
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
              {/* Route Selection Map */}
              <RouteMapSelector
                source={route.source}
                destination={route.destination}
                onRouteChange={(source: string, destination: string) => setRoute({ source, destination })}
              />

              {/* Tire Image Upload */}
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
                    onChange={(file, preview) => setFrontView({ file, preview })}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="full" className="mt-8 space-y-6">
              {/* Route Selection Map */}
              <RouteMapSelector
                source={route.source}
                destination={route.destination}
                onRouteChange={(source: string, destination: string) => setRoute({ source, destination })}
              />

              {/* Tire Image Uploads */}
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
                      onChange={(file, preview) => setFrontView({ file, preview })}
                    />
                    <ImageUpload
                      label="Side View"
                      description="Sidewall condition"
                      value={sideView.preview}
                      onChange={(file, preview) => setSideView({ file, preview })}
                    />
                    <ImageUpload
                      label="Closeup"
                      description="Wear details"
                      value={closeupView.preview}
                      onChange={(file, preview) => setCloseupView({ file, preview })}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

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
                    onChange={(event) => setTelemetry((current) => ({ ...current, tirePressurePsi: event.target.value }))}
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
                    onChange={(event) => setTelemetry((current) => ({ ...current, temperatureC: event.target.value }))}
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
                    onChange={(event) => setTelemetry((current) => ({ ...current, vibrationG: event.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="speed">Speed (km/h)</Label>
                  <Input
                    id="speed"
                    inputMode="decimal"
                    placeholder="80"
                    value={telemetry.speedKmph}
                    onChange={(event) => setTelemetry((current) => ({ ...current, speedKmph: event.target.value }))}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Analysis Progress */}
          {isAnalyzing && (
            <Card className="mb-8 border-primary/50 bg-primary/5">
              <CardContent className="py-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                    <span className="text-sm font-medium text-foreground">
                      Analyzing tire condition...
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {Math.round(progress)}%
                  </span>
                </div>
                <Progress value={progress} className="h-2" />
                <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-muted-foreground sm:grid-cols-4">
                  <div className={progress > 20 ? "text-primary" : ""}>
                    Preprocessing...
                  </div>
                  <div className={progress > 40 ? "text-primary" : ""}>
                    Feature extraction...
                  </div>
                  <div className={progress > 70 ? "text-primary" : ""}>
                    AI analysis...
                  </div>
                  <div className={progress > 90 ? "text-primary" : ""}>
                    Generating report...
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

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
                  Analyzing...
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
