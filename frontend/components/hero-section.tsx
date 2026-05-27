"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, Zap, Shield, BarChart3 } from "lucide-react"
import Link from "next/link"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-16">
      {/* Background gradient effect */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">
          <div className="h-150 w-150 rounded-full bg-primary/20 blur-[120px]" />
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8 lg:py-40">
        <div className="mx-auto max-w-3xl text-center">
          <Badge variant="secondary" className="mb-6 gap-1.5 px-3 py-1.5">
            <Zap className="h-3.5 w-3.5 text-primary" />
            AI-Powered Analysis
          </Badge>

          <h1 className="text-balance text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Intelligent Tire Health{" "}
            <span className="text-primary">Analysis</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground sm:text-xl">
            Upload a photo of your tire and get instant AI-powered assessment of tread depth,
            wear patterns, and personalized safety recommendations.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" className="gap-2" asChild>
              <Link href="/analyze">
                Start Free Analysis
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#how-it-works">See How It Works</Link>
            </Button>
          </div>

          {/* Stats */}
          <div className="mt-16 grid grid-cols-3 gap-8 border-t border-border/50 pt-10">
            <div className="flex flex-col items-center">
              <div className="text-3xl font-bold text-foreground sm:text-4xl">
                95%
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                Accuracy Rate
              </div>
            </div>
            <div className="flex flex-col items-center">
              <div className="text-3xl font-bold text-foreground sm:text-4xl">
                {"<2s"}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                Analysis Time
              </div>
            </div>
            <div className="flex flex-col items-center">
              <div className="text-3xl font-bold text-foreground sm:text-4xl">
                100K+
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                Tires Analyzed
              </div>
            </div>
          </div>
        </div>

        {/* Feature highlights */}
        <div className="mx-auto mt-20 grid max-w-4xl grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card/50 p-4 backdrop-blur-sm">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <BarChart3 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="font-medium text-foreground">Tread Depth</div>
              <div className="text-sm text-muted-foreground">±0.5mm precision</div>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card/50 p-4 backdrop-blur-sm">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="font-medium text-foreground">Safety Score</div>
              <div className="text-sm text-muted-foreground">Real-time risk</div>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card/50 p-4 backdrop-blur-sm">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="font-medium text-foreground">Life Prediction</div>
              <div className="text-sm text-muted-foreground">Miles remaining</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
