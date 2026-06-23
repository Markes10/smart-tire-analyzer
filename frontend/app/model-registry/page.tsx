import Link from "next/link"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getApiBaseUrl } from "@/lib/analyze"
import { GitBranch, RefreshCw } from "lucide-react"

type RegistryPayload = {
  generated_at?: string
  runtime_model?: string
  model_version?: string
  architecture?: Record<string, unknown>
  models?: Record<
    string,
    {
      best_weights?: string
      metadata?: string
      metrics?: string
      validation_metrics?: Record<string, unknown>
      test_metrics?: Record<string, unknown>
    }
  >
}

async function loadRegistry() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/registry`, {
      cache: "no-store",
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || `Registry request failed: ${response.status}`)
    }

    return {
      data: await response.json() as RegistryPayload,
      error: null,
    }
  } catch (err) {
    return {
      data: null,
      error: err instanceof Error ? err.message : "Registry unavailable",
    }
  }
}

export default async function ModelRegistryPage() {
  const { data, error } = await loadRegistry()
  const modelEntries = Object.entries(data?.models ?? {})

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 bg-muted/20 pt-24 pb-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="mb-8 flex items-center justify-between gap-4">
            <div>
              <div className="mb-2 flex items-center gap-2 text-primary">
                <GitBranch className="h-5 w-5" />
                <span className="text-sm font-medium uppercase tracking-wide">MLOps</span>
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Model Registry</h1>
              <p className="mt-2 text-muted-foreground">
                Browse promoted hybrid checkpoints and validation metrics from the backend registry.
              </p>
            </div>
            <Link
              href="/model-registry"
              className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-background"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Link>
          </div>

          {error && (
            <Card className="border-destructive/40">
              <CardHeader>
                <CardTitle>Registry unavailable</CardTitle>
                <CardDescription>{error}</CardDescription>
              </CardHeader>
            </Card>
          )}

          {data && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Active runtime</CardTitle>
                  <CardDescription>
                    Generated {data.generated_at ? new Date(data.generated_at).toLocaleString() : "unknown"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Badge>{data.runtime_model ?? "unknown"}</Badge>
                  <Badge variant="secondary">{data.model_version ?? "no version"}</Badge>
                </CardContent>
              </Card>

              {modelEntries.map(([name, entry]) => (
                <Card key={name}>
                  <CardHeader>
                    <CardTitle>{name}</CardTitle>
                    <CardDescription>Checkpoint artifacts and evaluation metrics</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm">
                    <div className="grid gap-2 md:grid-cols-2">
                      <div>Best weights: {entry.best_weights ?? "n/a"}</div>
                      <div>Metadata: {entry.metadata ?? "n/a"}</div>
                      <div>Metrics: {entry.metrics ?? "n/a"}</div>
                    </div>
                    {entry.validation_metrics && (
                      <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
                        {JSON.stringify(entry.validation_metrics, null, 2)}
                      </pre>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}
