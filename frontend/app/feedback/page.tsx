import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { TireFeedbackForm } from "@/components/tire-feedback-form"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { getFeedbackStats, type FeedbackStats } from "@/lib/feedback"
import { CheckCircle2, MessageSquare, RefreshCw, TrendingUp } from "lucide-react"

function formatAccuracy(value?: number) {
  if (value == null) return "--"
  return `${Math.round(value * 100)}%`
}

function formatRetrainQueue(stats?: FeedbackStats | null) {
  if (!stats) return "--"
  const pending = stats.pending_learning_rows ?? stats.pending_training ?? 0
  return stats.retrain_threshold ? `${pending}/${stats.retrain_threshold}` : String(pending)
}

function formatRetrainState(stats?: FeedbackStats | null) {
  if (!stats) return "--"
  if (stats.retrain_running) return "Running"
  if (stats.dataset_refresh_scheduled) return "Refreshing"
  return stats.retrain_ready ? "Ready" : "Monitoring"
}

async function loadFeedbackStats() {
  try {
    return {
      stats: await getFeedbackStats(),
      statsError: null,
    }
  } catch (err) {
    return {
      stats: undefined,
      statsError: err instanceof Error ? err.message : "Could not load feedback stats.",
    }
  }
}

export default async function FeedbackPage() {
  const { stats, statsError } = await loadFeedbackStats()

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="mb-12 text-center">
            <Badge variant="secondary" className="mb-4 gap-1.5">
              <MessageSquare className="h-3 w-3 text-primary" />
              Help Us Improve
            </Badge>
            <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Tire Analysis Feedback
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
              Submit corrections for completed tire analyses to improve tread depth, wear pattern, and safety predictions.
            </p>
          </div>

          <div className="mb-8 grid gap-4 md:grid-cols-3">
            <Card className="border-border/50 bg-card/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Feedback</p>
                    <p className="mt-1 text-2xl font-bold text-foreground">
                      {stats?.total_feedback ?? "--"}
                    </p>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    <MessageSquare className="h-6 w-6 text-primary" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Confirmed Correct</p>
                    <p className="mt-1 text-2xl font-bold text-foreground">
                      {formatAccuracy(stats?.accuracy_rate)}
                    </p>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success/10">
                    <TrendingUp className="h-6 w-6 text-success" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Retraining</p>
                    <p className="mt-1 text-2xl font-bold text-foreground">
                      {formatRetrainState(stats)}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Queue {formatRetrainQueue(stats)}
                    </p>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    {stats?.retrain_ready ? (
                      <CheckCircle2 className="h-6 w-6 text-success" />
                    ) : (
                      <RefreshCw className="h-6 w-6 text-primary" />
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {statsError && (
            <p className="mb-6 text-center text-sm text-muted-foreground">
              Feedback stats are unavailable: {statsError}
            </p>
          )}

          <TireFeedbackForm />
        </div>
      </main>
      <Footer />
    </div>
  )
}
