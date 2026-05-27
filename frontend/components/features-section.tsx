import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Activity,
  Boxes,
  Cloud,
  Cpu,
  Database,
  Eye,
  FileText,
  Gauge,
  Lock,
  Network,
  RadioTower,
  TrendingUp,
  Workflow,
} from "lucide-react"

const features = [
  {
    icon: Workflow,
    title: "MLOps Pipeline",
    description: "Dataset versioning, experiment tracking, model registry, CI/CD deployment, monitoring, and retraining.",
  },
  {
    icon: Cpu,
    title: "Edge AI",
    description: "ONNX, TensorRT, Jetson, and mobile inference readiness for offline local predictions.",
  },
  {
    icon: Eye,
    title: "Explainable AI",
    description: "Grad-CAM, SHAP, and attention heatmap metadata that highlights tire damage regions.",
  },
  {
    icon: Gauge,
    title: "Confidence Scoring",
    description: "Prediction confidence, uncertainty estimation, and failure risk scoring in every report.",
  },
  {
    icon: Boxes,
    title: "Digital Twin",
    description: "A virtual tire lifecycle simulation linked to the physical tire state and forecast.",
  },
  {
    icon: TrendingUp,
    title: "Predictive Analytics",
    description: "Remaining useful life, future failure forecast, and wear trend analysis.",
  },
  {
    icon: RadioTower,
    title: "IoT Fusion",
    description: "Pressure, temperature, vibration, speed, and image data combined into a multimodal AI layer.",
  },
  {
    icon: Cloud,
    title: "Cloud Native",
    description: "Docker, Kubernetes, and microservice deployment status for production-style delivery.",
  },
  {
    icon: Lock,
    title: "Security Layer",
    description: "Optional JWT, RBAC, API gateway guard, and encryption architecture for enterprise demos.",
  },
  {
    icon: Activity,
    title: "Monitoring",
    description: "Dashboard visibility into drift, health, GPU status, latency, feedback, and errors.",
  },
  {
    icon: Network,
    title: "Multi-Agent AI",
    description: "Damage, maintenance, cost, and report agents create autonomous recommendations.",
  },
  {
    icon: Database,
    title: "RAG Knowledge Base",
    description: "Maintenance knowledge retrieval with FAISS and Pinecone-ready extension points.",
  },
  {
    icon: FileText,
    title: "LLM Reports",
    description: "Llama/Ollama-ready report generation with technician notes and PDF-ready metadata.",
  },
]

export function FeaturesSection() {
  return (
    <section id="features" className="border-t border-border/50 bg-card/30">
      <div className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Everything you need for tire intelligence
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            A comprehensive AI-powered platform that transforms tire maintenance from reactive to predictive.
          </p>
        </div>

        <div className="mx-auto mt-16 grid max-w-6xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <Card 
              key={feature.title} 
              className="group border-border/50 bg-card/50 transition-all hover:border-primary/50 hover:bg-card"
            >
              <CardHeader className="pb-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 transition-colors group-hover:bg-primary/20">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <CardTitle className="mt-4 text-lg">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
