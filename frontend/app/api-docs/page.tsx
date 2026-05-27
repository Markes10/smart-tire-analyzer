"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Check, Copy, Gauge, History, MessageSquare, ShieldCheck } from "lucide-react"

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "Set NEXT_PUBLIC_API_BASE_URL"

const endpoints = [
  {
    method: "POST",
    path: "/analyze",
    description: "Analyze a tread image with optional sidewall image and road/weather coordinates.",
    request: `multipart/form-data
image: File (required)
sidewall_image: File (optional)
latitude: number (optional)
longitude: number (optional)
tire_brand: string (optional)
tire_model: string (optional)
tire_size: string (optional)
mileage_km: number (optional)`,
    response: `{
  "session_id": "uuid",
  "risk_level": "LOW | MODERATE | HIGH | CRITICAL",
  "status": "ACCEPTABLE - Continue normal monitoring",
  "confidence": 0.91,
  "predictions": {
    "tread_depths_mm": { "average": 6.2, "min": 5.8, "max": 6.6 },
    "health_score": 7.8,
    "remaining_life_km": 42000,
    "wear_pattern": { "label": "uniform_wear", "severity": "low" }
  }
}`,
  },
  {
    method: "GET",
    path: "/history",
    description: "Return paginated analysis history saved by the backend database.",
    request: `Query parameters:
page=1
page_size=20
risk_level=LOW
from_date=2026-05-01
to_date=2026-05-14`,
    response: `{
  "total": 1,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "session_id": "uuid",
      "risk_level": "LOW",
      "health_score": 7.8,
      "avg_tread_mm": 6.2
    }
  ]
}`,
  },
  {
    method: "GET",
    path: "/history/{session_id}",
    description: "Fetch one full analysis report by session ID.",
    request: "No request body.",
    response: `{
  "session_id": "uuid",
  "predictions": { "...": "full report" },
  "reasoning": { "...": "recommendation details" }
}`,
  },
  {
    method: "POST",
    path: "/feedback",
    description: "Submit a user correction for continuous learning.",
    request: `{
  "session_id": "uuid",
  "feedback_type": "wrong | inaccurate | correct | partial",
  "corrected_tread_depth_mm": 4.8,
  "corrected_wear_pattern": "uniform_wear",
  "comment": "Measured manually after scan"
}`,
    response: `{
  "feedback_id": "uuid",
  "session_id": "uuid",
  "stored": true,
  "retrain_triggered": false
}`,
  },
  {
    method: "GET",
    path: "/health",
    description: "Check API and model liveness.",
    request: "No request body.",
    response: `{
  "status": "alive",
  "components": {
    "api": "ready",
    "model": "ready"
  }
}`,
  },
  {
    method: "GET",
    path: "/enterprise/dashboard",
    description: "Return MLOps, monitoring, edge AI, security, federated learning, and deployment status.",
    request: "No request body.",
    response: `{
  "architecture": { "modules": ["MLOps", "Edge AI", "XAI", "..."] },
  "monitoring": {
    "model_drift_detection": { "status": "stable" },
    "system_health": "ready_for_local_demo"
  },
  "mlops": {
    "dataset_versioning": { "dataset_fingerprint": "..." },
    "model_registry": { "registered": true }
  }
}`,
  },
  {
    method: "POST",
    path: "/enterprise/simulate",
    description: "Run the enterprise AI extension layer with sample predictions and optional IoT telemetry.",
    request: `{
  "risk_level": "HIGH",
  "confidence": 0.92,
  "tire_pressure_psi": 28,
  "temperature_c": 55,
  "vibration_g": 1.4,
  "speed_kmph": 90
}`,
    response: `{
  "confidence_estimation": {
    "prediction_confidence_pct": 92,
    "failure_risk_label": "High"
  },
  "digital_twin": { "sync_pattern": "Physical Tyre <-> Virtual AI Simulation" },
  "multi_agent_ai": { "autonomous_ai_ecosystem": true }
}`,
  },
]

const codeExamples = {
  curl: `curl -X POST "${apiBaseUrl}/analyze" \\
  -F "image=@tire_image.jpg" \\
  -F "latitude=28.6139" \\
  -F "longitude=77.2090"`,
  javascript: `const formData = new FormData();
formData.append("image", fileInput.files[0]);

const response = await fetch("${apiBaseUrl}/analyze", {
  method: "POST",
  body: formData,
});

const result = await response.json();`,
  python: `import requests

with open("tire_image.jpg", "rb") as image:
    response = requests.post(
        "${apiBaseUrl}/analyze",
        files={"image": image},
    )

print(response.json())`,
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative">
      <pre className="overflow-x-auto rounded-lg bg-muted/50 p-4 text-sm">
        <code className="text-foreground">{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-8 w-8"
        onClick={handleCopy}
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </Button>
    </div>
  )
}

export default function APIDocsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <section className="border-b border-border/50 py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <Badge className="mb-4">Runtime API</Badge>
            <h1 className="text-4xl font-bold tracking-tight text-foreground">API Documentation</h1>
            <p className="mt-4 max-w-3xl text-muted-foreground">
              These are the routes implemented by the current FastAPI backend. Base URL is read from
              <code className="mx-1 rounded bg-muted px-1.5 py-0.5">NEXT_PUBLIC_API_BASE_URL</code>.
            </p>
          </div>
        </section>

        <section className="border-b border-border/50 py-10">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 sm:grid-cols-3 sm:px-6 lg:px-8">
            {[
              { icon: Gauge, title: "Model-backed", description: "The analysis endpoint calls the loaded tire model." },
              { icon: History, title: "Persistent", description: "Reports are saved and listed through history APIs." },
              { icon: ShieldCheck, title: "Config driven", description: "URLs and API keys come from environment variables." },
            ].map((feature) => (
              <div key={feature.title} className="flex items-center gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid gap-8 lg:grid-cols-2">
              <Card className="border-border/50 bg-card/50">
                <CardHeader>
                  <CardTitle>Base URL</CardTitle>
                  <CardDescription>Configured frontend backend URL</CardDescription>
                </CardHeader>
                <CardContent>
                  <CodeBlock code={apiBaseUrl} />
                </CardContent>
              </Card>
              <Card className="border-border/50 bg-card/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5 text-primary" />
                    First Request
                  </CardTitle>
                  <CardDescription>Upload a single tire image</CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="curl">
                    <TabsList>
                      <TabsTrigger value="curl">cURL</TabsTrigger>
                      <TabsTrigger value="javascript">JavaScript</TabsTrigger>
                      <TabsTrigger value="python">Python</TabsTrigger>
                    </TabsList>
                    <TabsContent value="curl" className="mt-4">
                      <CodeBlock code={codeExamples.curl} />
                    </TabsContent>
                    <TabsContent value="javascript" className="mt-4">
                      <CodeBlock code={codeExamples.javascript} />
                    </TabsContent>
                    <TabsContent value="python" className="mt-4">
                      <CodeBlock code={codeExamples.python} />
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            </div>

            <div className="mt-12 space-y-8">
              {endpoints.map((endpoint) => (
                <Card key={`${endpoint.method}-${endpoint.path}`} className="border-border/50 bg-card/80">
                  <CardHeader>
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge variant={endpoint.method === "GET" ? "outline" : "default"}>
                        {endpoint.method}
                      </Badge>
                      <code className="text-lg font-mono text-foreground">{endpoint.path}</code>
                    </div>
                    <CardDescription className="mt-2">{endpoint.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Tabs defaultValue="request">
                      <TabsList>
                        <TabsTrigger value="request">Request</TabsTrigger>
                        <TabsTrigger value="response">Response</TabsTrigger>
                      </TabsList>
                      <TabsContent value="request" className="mt-4">
                        <CodeBlock code={endpoint.request} />
                      </TabsContent>
                      <TabsContent value="response" className="mt-4">
                        <CodeBlock code={endpoint.response} />
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
