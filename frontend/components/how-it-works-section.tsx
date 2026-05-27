import { Badge } from "@/components/ui/badge"

const steps = [
  {
    step: "01",
    title: "Upload Tire Image",
    description: "Take a photo of your tire using your phone or upload an existing image. Our system supports front, side, and closeup views for comprehensive analysis.",
  },
  {
    step: "02",
    title: "AI Analysis",
    description: "Our multi-model AI stack processes your image through CNN, Transformer, and RNN layers to extract tread depth, wear patterns, and damage indicators.",
  },
  {
    step: "03",
    title: "Context Enhancement",
    description: "We integrate weather data and road conditions from your location to provide contextual driving recommendations tailored to your environment.",
  },
  {
    step: "04",
    title: "Get Your Report",
    description: "Receive a comprehensive Smart Tire Report with health scores, risk assessment, and personalized maintenance recommendations in under 2 seconds.",
  },
]

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="border-t border-border/50">
      <div className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <Badge variant="secondary" className="mb-4">Process</Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            How it works
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            From photo to actionable insights in seconds
          </p>
        </div>

        <div className="mx-auto mt-16 max-w-4xl">
          <div className="relative">
            {/* Connecting line */}
            <div className="absolute left-5.75 top-0 hidden h-full w-px bg-linear-to-b from-primary via-primary/50 to-transparent sm:block" />

            <div className="space-y-12">
              {steps.map((item) => (
                <div key={item.step} className="relative flex gap-6">
                  <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-primary/50 bg-background text-sm font-bold text-primary">
                    {item.step}
                  </div>
                  <div className="flex-1 pt-1.5">
                    <h3 className="text-xl font-semibold text-foreground">
                      {item.title}
                    </h3>
                    <p className="mt-2 leading-relaxed text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
