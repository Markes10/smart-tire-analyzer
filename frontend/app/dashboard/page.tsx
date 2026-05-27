"use client"

import { useEffect, useMemo, useState } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { getApiBaseUrl } from "@/lib/analyze"
import {
  Activity,
  Boxes,
  Brain,
  Cloud,
  Cpu,
  Database,
  GitBranch,
  Lock,
  Network,
  RadioTower,
  RefreshCw,
  ShieldCheck,
} from "lucide-react"

type DashboardPayload = Record<string, any>

const moduleIcons: Record<string, any> = {
  mlops: GitBranch,
  edge_ai: Cpu,
  xai: Brain,
  confidence: ShieldCheck,
  digital_twin: Boxes,
  predictive: Activity,
  iot: RadioTower,
  cloud: Cloud,
  security: Lock,
  monitoring: Activity,
  agents: Network,
  federated: RefreshCw,
  rag: Database,
  llm_report: Brain,
  synthetic_data: Boxes,
}

function statusVariant(value: string) {
  const normalized = value.toLowerCase()
  if (normalized.includes("ready") || normalized.includes("stable") || normalized.includes("online")) return "default"
  if (normalized.includes("watch") || normalized.includes("warning")) return "secondary"
  return "outline"
}

export default function EnterpriseDashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    fetch(`${getApiBaseUrl()}/enterprise/dashboard`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`Dashboard request failed: ${response.status}`)
        return response.json()
      })
      .then((payload) => {
        if (mounted) setData(payload)
      })
      .catch((err) => {
        if (mounted) setError(err instanceof Error ? err.message : "Dashboard unavailable")
      })
    return () => {
      mounted = false
    }
  }, [])

  const modules = useMemo(() => data?.architecture?.modules ?? [], [data])
  const implemented = modules.length
  const maturity = modules.length ? Math.round((implemented / 15) * 100) : 0

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <section className="border-b border-border/50 py-12">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <Badge className="mb-4 gap-1.5">
                  <Activity className="h-3.5 w-3.5" />
                  Enterprise AI
                </Badge>
                <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                  MLOps & Monitoring Dashboard
                </h1>
                <p className="mt-3 max-w-2xl text-muted-foreground">
                  Model lifecycle, edge AI, explainability, IoT fusion, digital twin, federated learning, RAG, and cloud deployment status.
                </p>
              </div>
              <Card className="w-full border-border/50 bg-card/50 lg:w-80">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Architecture Maturity</CardTitle>
                  <CardDescription>{implemented} of 15 modules connected</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Final year project scope</span>
                    <span className="font-medium text-foreground">{maturity}%</span>
                  </div>
                  <Progress value={maturity} className="h-2" />
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        <section className="py-10">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {error && (
              <Card className="mb-8 border-destructive/50 bg-destructive/5">
                <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
              </Card>
            )}

            {!data && !error && (
              <div className="py-20 text-center text-sm text-muted-foreground">Loading dashboard...</div>
            )}

            {data && (
              <div className="space-y-8">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {[
                    {
                      title: "Model Drift",
                      value: data.monitoring?.model_drift_detection?.status ?? "stable",
                      icon: Activity,
                    },
                    {
                      title: "GPU",
                      value: data.monitoring?.gpu_usage?.device ?? "cpu",
                      icon: Cpu,
                    },
                    {
                      title: "Security",
                      value: data.security?.jwt_authentication ?? "available",
                      icon: Lock,
                    },
                    {
                      title: "Deployment",
                      value: data.deployment?.deployment_maturity ?? "cloud_native_ready",
                      icon: Cloud,
                    },
                  ].map((item) => (
                    <Card key={item.title} className="border-border/50 bg-card/50">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <item.icon className="h-4 w-4 text-primary" />
                          {item.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Badge variant={statusVariant(String(item.value))}>{String(item.value)}</Badge>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                  {modules.map((module: any) => {
                    const Icon = moduleIcons[module.id] ?? Boxes
                    return (
                      <Card key={module.id} className="border-border/50 bg-card/50">
                        <CardHeader>
                          <CardTitle className="flex items-center gap-2 text-lg">
                            <Icon className="h-5 w-5 text-primary" />
                            {module.name}
                          </CardTitle>
                          <CardDescription>{module.tools?.join(" | ")}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Badge variant={statusVariant(module.local_status)}>{module.local_status}</Badge>
                          <div className="flex flex-wrap gap-2">
                            {(module.capabilities ?? []).map((capability: string) => (
                              <Badge key={capability} variant="outline">
                                {capability}
                              </Badge>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>

                <div className="grid gap-6 lg:grid-cols-2">
                  <Card className="border-border/50 bg-card/50">
                    <CardHeader>
                      <CardTitle>MLOps Lifecycle</CardTitle>
                      <CardDescription>Dataset versioning, experiment tracking, registry, deployment, monitoring</CardDescription>
                    </CardHeader>
                    <CardContent className="grid gap-3 text-sm text-muted-foreground">
                      <div>Dataset fingerprint: {data.mlops?.dataset_versioning?.dataset_fingerprint}</div>
                      <div>MLflow: {data.mlops?.experiment_tracking?.mlflow_available ? "available" : "optional"}</div>
                      <div>W&B: {data.mlops?.experiment_tracking?.weights_biases_available ? "available" : "optional"}</div>
                      <div>Model registry: {data.mlops?.model_registry?.registered ? "registered" : "waiting for training"}</div>
                    </CardContent>
                  </Card>

                  <Card className="border-border/50 bg-card/50">
                    <CardHeader>
                      <CardTitle>Monitoring</CardTitle>
                      <CardDescription>Drift, health, latency, logs, feedback loop</CardDescription>
                    </CardHeader>
                    <CardContent className="grid gap-3 text-sm text-muted-foreground">
                      <div>System health: {data.monitoring?.system_health}</div>
                      <div>Error logs: {data.monitoring?.error_logs?.status}</div>
                      <div>Total feedback: {data.monitoring?.feedback_loop?.total_feedback ?? 0}</div>
                      <div>Auto retraining: {data.monitoring?.model_drift_detection?.auto_retraining ? "enabled" : "disabled"}</div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
