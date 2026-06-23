import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Card, CardContent } from "@/components/ui/card"
import { Gauge, Shield, Zap, Users, Target, Heart } from "lucide-react"
import Image from "next/image"

const stats = [
  { label: "Analyses Performed", value: "2M+" },
  { label: "Active Users", value: "50K+" },
  { label: "Fleet Partners", value: "500+" },
  { label: "Prediction Accuracy", value: "95%" },
]

const values = [
  {
    icon: Shield,
    title: "Safety First",
    description: "Every feature we build prioritizes road safety and accident prevention through early tire issue detection.",
  },
  {
    icon: Zap,
    title: "Innovation",
    description: "We leverage cutting-edge AI models including CNNs, Transformers, and continuous learning systems.",
  },
  {
    icon: Users,
    title: "Accessibility",
    description: "Making professional-grade tire analysis available to everyone, from individual drivers to large fleets.",
  },
  {
    icon: Target,
    title: "Precision",
    description: "Our multi-model architecture ensures accurate predictions with confidence thresholds and self-correction.",
  },
  {
    icon: Heart,
    title: "User-Centric",
    description: "We design every interaction to be intuitive, informative, and actionable for real-world use.",
  },
  {
    icon: Gauge,
    title: "Reliability",
    description: "Built for 99.9% uptime with robust infrastructure that scales to millions of daily analyses.",
  },
]

const team = [
  { name: "Dweepan Gain", image: "/team/dweepan-gain.png" },
  { name: "Shivam R. Bandekar", image: "/team/shivam-r-bandekar.png" },
  { name: "Viren", image: "/team/viren.png" },
  { name: "Shubham S. Chodankar", image: "/team/shubham-s-chodankar.png" },
]

export default function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        {/* Hero Section */}
        <section className="relative overflow-hidden py-24 sm:py-32">
          <div className="absolute inset-0 -z-10">
            <div className="absolute left-1/2 top-0 -translate-x-1/2">
              <div className="h-150 w-150 rounded-full bg-primary/10 blur-[120px]" />
            </div>
          </div>

          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl text-center">
              <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
                Making Roads Safer with AI
              </h1>
              <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
                Smart Tire Analyzer was founded with a simple mission: use artificial intelligence
                to prevent tire-related accidents and help drivers make informed decisions about
                their vehicle&apos;s safety.
              </p>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="border-y border-border/50 bg-muted/20 py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center">
                  <p className="text-3xl font-bold text-primary sm:text-4xl">{stat.value}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Story Section */}
        <section className="py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-3xl">
              <h2 className="text-3xl font-bold tracking-tight text-foreground">Our Story</h2>
              <div className="mt-8 space-y-6 text-muted-foreground leading-relaxed">
                <p>
                  In 2021, our founders witnessed a preventable accident caused by tire failure.
                  This experience sparked a question: why isn&apos;t tire health monitoring as
                  accessible as checking your phone&apos;s battery?
                </p>
                <p>
                  Traditional tire inspections require expensive equipment and trained technicians.
                  We knew AI could change this. By combining computer vision with deep learning,
                  we built a system that anyone can use with just their smartphone camera.
                </p>
                <p>
                  Today, Smart Tire Analyzer processes over 50,000 tire analyses daily, helping
                  individual drivers, fleet managers, and auto service centers make data-driven
                  decisions about tire maintenance and replacement.
                </p>
                <p>
                  Our multi-model AI architecture combines CNNs for visual feature extraction,
                  Transformers for pattern recognition, and RNNs for sequential tread analysis.
                  This ensemble approach, combined with our continuous learning pipeline, ensures
                  our predictions become more accurate over time.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Values Section */}
        <section className="bg-muted/20 py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-foreground">Our Values</h2>
              <p className="mt-4 text-muted-foreground">
                The principles that guide everything we build
              </p>
            </div>
            <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
              {values.map((value) => (
                <Card key={value.title} className="border-border/50 bg-card/50">
                  <CardContent className="pt-6">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                      <value.icon className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold text-foreground">{value.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {value.description}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Team Section */}
        <section className="py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-foreground">Leadership Team</h2>
              <p className="mt-4 text-muted-foreground">
                Industry veterans building the future of tire safety
              </p>
            </div>
            <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {team.map((member) => (
                <div key={member.name} className="text-center">
                  <div className="relative mx-auto h-32 w-32 overflow-hidden rounded-full bg-muted/50">
                    <Image
                      src={member.image}
                      alt={member.name}
                      fill
                      sizes="128px"
                      className="object-cover"
                    />
                  </div>
                  <h3 className="mt-6 text-lg font-semibold text-foreground">{member.name}</h3>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
