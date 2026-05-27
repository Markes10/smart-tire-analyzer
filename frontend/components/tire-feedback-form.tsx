"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { ImageUpload } from "@/components/image-upload"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { submitFeedback, type FeedbackResponse } from "@/lib/feedback"
import { CheckCircle2, AlertTriangle, Send, RotateCcw } from "lucide-react"

interface TireImage {
  file: File | null
  preview: string | null
}

const WEAR_PATTERN_OPTIONS = [
  { value: "even", label: "Even wear" },
  { value: "center_wear", label: "Center wear" },
  { value: "edge_wear", label: "Edge wear" },
  { value: "uneven_wear", label: "Uneven wear" },
  { value: "one_sided_wear", label: "One-sided wear" },
  { value: "critical_wear", label: "Critical wear" },
]

export function TireFeedbackForm() {
  const [tireImages, setTireImages] = useState<TireImage>({ file: null, preview: null })
  const [sidewallImages, setSidewallImages] = useState<TireImage>({ file: null, preview: null })
  const [sessionId, setSessionId] = useState("")
  const [originalPrediction, setOriginalPrediction] = useState<Record<string, any> | undefined>()
  const [treadDepths, setTreadDepths] = useState(["", "", "", ""])
  const [correctedWearPattern, setCorrectedWearPattern] = useState("unspecified")
  const [feedback, setFeedback] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitResult, setSubmitResult] = useState<FeedbackResponse | null>(null)

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("smart-tire:last-analysis")
      if (!stored) return

      const parsed = JSON.parse(stored) as Record<string, any>
      if (typeof parsed.session_id === "string") {
        setSessionId(parsed.session_id)
        setOriginalPrediction(parsed)
      }
    } catch {
      // Session storage is only a convenience; the user can paste a session ID.
    }
  }, [])

  const handleTreadDepthChange = (index: number, value: string) => {
    const newDepths = [...treadDepths]
    newDepths[index] = value
    setTreadDepths(newDepths)
  }

  const allTreadDepthsFilled = treadDepths.every(depth => depth !== "")
  const avgTreadDepth = allTreadDepthsFilled
    ? (treadDepths.reduce((sum, depth) => sum + parseFloat(depth), 0) / 4).toFixed(1)
    : null

  const hasAllInputs = sessionId.trim() && allTreadDepthsFilled && feedback.trim()

  const handleReset = () => {
    setTireImages({ file: null, preview: null })
    setSidewallImages({ file: null, preview: null })
    setSessionId(originalPrediction?.session_id ?? "")
    setTreadDepths(["", "", "", ""])
    setCorrectedWearPattern("unspecified")
    setFeedback("")
    setSubmitSuccess(false)
    setSubmitError(null)
    setSubmitResult(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setSubmitError(null)
    setSubmitSuccess(false)

    try {
      const numericDepths = treadDepths.map((depth) => Number(depth))
      if (!numericDepths.every((depth) => Number.isFinite(depth) && depth >= 0 && depth <= 12)) {
        throw new Error("Enter tread depth values between 0 and 12 mm.")
      }

      const averageDepth = numericDepths.reduce((sum, depth) => sum + depth, 0) / numericDepths.length
      const result = await submitFeedback({
        session_id: sessionId.trim(),
        feedback_type: "wrong",
        corrected_tread_depth_mm: Number(averageDepth.toFixed(2)),
        corrected_tread_depths_mm: {
          tread_1: numericDepths[0],
          tread_2: numericDepths[1],
          tread_3: numericDepths[2],
          tread_4: numericDepths[3],
        },
        corrected_wear_pattern: correctedWearPattern === "unspecified" ? undefined : correctedWearPattern,
        original_prediction: originalPrediction,
        confidence_override: 0.9,
        comment: feedback.trim(),
      })

      setSubmitResult(result)
      setSubmitSuccess(true)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Feedback submission failed.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitSuccess) {
    return (
      <Card className="border-green-200/50 bg-green-50/30 dark:border-green-900/30 dark:bg-green-950/20">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/50">
            <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">Feedback Submitted Successfully</h3>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            {submitResult?.message ?? "Thank you for contributing to our tire analysis database."}
          </p>
          {submitResult && (
            <p className="mt-3 text-center text-xs text-muted-foreground">
              Pending learning rows: {submitResult.pending_learning_rows ?? 0} / {submitResult.retrain_threshold ?? "--"}
            </p>
          )}
          <Button onClick={handleReset} className="mt-6 gap-2">
            <RotateCcw className="h-4 w-4" />
            Submit Another Feedback
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Image Uploads */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-primary" />
            Tire Images
          </CardTitle>
          <CardDescription>
            Optional reference photos. Corrections are linked to a completed analysis session.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <ImageUpload
              label="Tire Tread"
              description="Front view of tire tread pattern"
              value={tireImages.preview}
              onChange={(file, preview) => setTireImages({ file, preview })}
            />
            <ImageUpload
              label="Sidewall"
              description="Side view showing sidewall condition and markings"
              value={sidewallImages.preview}
              onChange={(file, preview) => setSidewallImages({ file, preview })}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            Analysis Session
          </CardTitle>
          <CardDescription>
            Feedback must reference a backend analysis result so the saved image can be used for retraining.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Label htmlFor="session-id">Session ID</Label>
          <Input
            id="session-id"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="Paste analysis session ID"
            className="font-mono text-sm"
          />
        </CardContent>
      </Card>

      {/* Tread Depth Input */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-primary" />
            Tread Depth Measurement
          </CardTitle>
          <CardDescription>
            Measure tread depth at 4 different points on the tire using a depth gauge (inner, center, outer edges)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            {[1, 2, 3, 4].map((position) => (
              <div key={position} className="space-y-2">
                <Label htmlFor={`tread-depth-${position}`}>
                  Measurement {position} (mm)
                </Label>
                <div className="relative">
                  <Input
                    id={`tread-depth-${position}`}
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="e.g., 5.2"
                    value={treadDepths[position - 1]}
                    onChange={(e) => handleTreadDepthChange(position - 1, e.target.value)}
                    className="pr-12"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                    mm
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Average Tread Depth Display */}
          {avgTreadDepth !== null && (
            <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-foreground">Average Tread Depth</p>
                <p className="text-xs text-muted-foreground">Calculated from 4 measurements</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-primary">{avgTreadDepth}</p>
                <p className="text-xs text-muted-foreground">mm</p>
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Minimum safe tread depth is 1.6mm
          </p>

          {avgTreadDepth && parseFloat(avgTreadDepth) < 1.6 && (
            <Alert className="border-red-200/50 bg-red-50/30 dark:border-red-900/30 dark:bg-red-950/20">
              <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
              <AlertDescription className="ml-2 text-sm text-red-700 dark:text-red-300">
                This tire is below the legal minimum tread depth. Replacement is recommended.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-primary" />
            Wear Pattern Correction
          </CardTitle>
          <CardDescription>
            Select the closest visible wear pattern if the analysis classification was wrong.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Label htmlFor="wear-pattern">Wear Pattern</Label>
          <Select value={correctedWearPattern} onValueChange={setCorrectedWearPattern}>
            <SelectTrigger id="wear-pattern" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="unspecified">Not sure</SelectItem>
              {WEAR_PATTERN_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Feedback Section */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            Additional Feedback
          </CardTitle>
          <CardDescription>
            Share your observations about the tire condition and any other relevant information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="feedback">Your Feedback</Label>
            <Textarea
              id="feedback"
              placeholder="Describe the tire's condition, any visible damage, wear patterns, or other observations..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              maxLength={1000}
              className="min-h-32 resize-none"
            />
            <p className="text-xs text-muted-foreground">
              {feedback.length} / 1000 characters
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Info Alert */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Your correction is sent to the backend feedback API and added to the continuous-learning queue for validated retraining.
        </AlertDescription>
      </Alert>

      {submitError && (
        <Alert className="border-destructive/50 bg-destructive/5">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <AlertDescription className="text-destructive">{submitError}</AlertDescription>
        </Alert>
      )}

      {/* Submit Buttons */}
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Button
          type="submit"
          size="lg"
          disabled={!hasAllInputs || isSubmitting}
          className="gap-2"
        >
          {isSubmitting ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Submitting...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Submit Feedback
            </>
          )}
        </Button>
        {(tireImages.preview || sidewallImages.preview || treadDepths.some(d => d) || correctedWearPattern !== "unspecified" || feedback) && (
          <Button
            type="button"
            size="lg"
            variant="outline"
            onClick={handleReset}
            className="gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Clear
          </Button>
        )}
      </div>

      {!hasAllInputs && (
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <AlertTriangle className="h-4 w-4" />
          Add a session ID, four tread measurements, and feedback notes to submit
        </div>
      )}
    </form>
  )
}
