"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import {
    Building2,
    CheckCircle2,
    Users,
    Shield,
    Zap,
    BarChart3,
    Headphones,
    Lock,
    Globe,
    Server
} from "lucide-react"
import { enterpriseSalesSchema, type EnterpriseSalesInput } from "@/lib/validation"

const enterpriseFeatures = [
    {
        icon: Users,
        title: "Unlimited Team Members",
        description: "Add your entire fleet management team with role-based access controls."
    },
    {
        icon: Shield,
        title: "Advanced Security",
        description: "SSO, SAML, and enterprise-grade encryption for your data."
    },
    {
        icon: Zap,
        title: "Priority Processing",
        description: "Dedicated resources ensure fastest analysis times for your fleet."
    },
    {
        icon: BarChart3,
        title: "Custom Analytics",
        description: "Tailored dashboards and reports specific to your business needs."
    },
    {
        icon: Headphones,
        title: "Dedicated Support",
        description: "24/7 priority support with a dedicated account manager."
    },
    {
        icon: Lock,
        title: "Data Compliance",
        description: "GDPR, SOC 2, and industry-specific compliance certifications."
    },
    {
        icon: Globe,
        title: "API Access",
        description: "Full API access for seamless integration with your existing systems."
    },
    {
        icon: Server,
        title: "On-Premise Option",
        description: "Deploy on your own infrastructure for maximum control."
    },
]

const testimonials = [
    {
        quote: "Smart Tire Analyzer has reduced our fleet maintenance costs by 35% and prevented countless roadside breakdowns.",
        author: "Michael Chen",
        role: "Fleet Director",
        company: "National Logistics Corp",
        fleet: "2,500+ vehicles"
    },
    {
        quote: "The predictive maintenance alerts have been a game-changer. We now replace tires proactively instead of reactively.",
        author: "Sarah Williams",
        role: "Operations Manager",
        company: "TransContinental Shipping",
        fleet: "800+ trucks"
    },
]

const fleetSizes = [
    { value: "10-50", label: "10-50 vehicles" },
    { value: "51-200", label: "51-200 vehicles" },
    { value: "201-500", label: "201-500 vehicles" },
    { value: "501-1000", label: "501-1,000 vehicles" },
    { value: "1000+", label: "1,000+ vehicles" },
]

export default function EnterpriseSalesPage() {
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)

    const {
        register,
        handleSubmit,
        formState: { errors },
        setValue,
        reset,
    } = useForm<EnterpriseSalesInput>({
        resolver: zodResolver(enterpriseSalesSchema),
    })

    const onSubmit = async (data: EnterpriseSalesInput) => {
        setIsSubmitting(true)
        await new Promise(resolve => setTimeout(resolve, 1500))
        setIsSubmitting(false)
        setIsSubmitted(true)
    }

    return (
        <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1 pt-16">
                {/* Hero Section */}
                <section className="relative overflow-hidden py-24">
                    <div className="absolute inset-0 -z-10">
                        <div className="absolute left-1/2 top-0 -translate-x-1/2">
                            <div className="h-150 w-150 rounded-full bg-primary/10 blur-[120px]" />
                        </div>
                    </div>

                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <div className="mx-auto max-w-3xl text-center">
                            <Badge variant="secondary" className="mb-4">Enterprise Solutions</Badge>
                            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
                                Fleet Tire Management at Scale
                            </h1>
                            <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
                                Join hundreds of fleet operators who trust Smart Tire Analyzer to keep their
                                vehicles safe, reduce maintenance costs, and optimize tire lifecycles.
                            </p>
                            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <CheckCircle2 className="h-4 w-4 text-primary" />
                                    <span>Custom pricing</span>
                                </div>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <CheckCircle2 className="h-4 w-4 text-primary" />
                                    <span>Dedicated support</span>
                                </div>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <CheckCircle2 className="h-4 w-4 text-primary" />
                                    <span>SLA guarantee</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Features Grid */}
                <section className="border-y border-border/50 bg-muted/30 py-24">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <div className="text-center">
                            <h2 className="text-3xl font-bold text-foreground">Enterprise Features</h2>
                            <p className="mt-4 text-muted-foreground">
                                Everything you need to manage tire health across your entire fleet
                            </p>
                        </div>
                        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                            {enterpriseFeatures.map((feature) => (
                                <Card key={feature.title} className="border-border/50 bg-card/80">
                                    <CardContent className="pt-6">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                            <feature.icon className="h-5 w-5 text-primary" />
                                        </div>
                                        <h3 className="mt-4 font-semibold text-foreground">{feature.title}</h3>
                                        <p className="mt-2 text-sm text-muted-foreground">{feature.description}</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Contact Form & Testimonials */}
                <section className="py-24">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <div className="grid gap-12 lg:grid-cols-2">
                            {/* Contact Form */}
                            <Card className="border-border/50 bg-card/50">
                                <CardHeader>
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                            <Building2 className="h-5 w-5 text-primary" />
                                        </div>
                                        <div>
                                            <CardTitle>Contact Enterprise Sales</CardTitle>
                                            <CardDescription>
                                                Tell us about your fleet and we will create a custom solution
                                            </CardDescription>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    {isSubmitted ? (
                                        <div className="flex flex-col items-center justify-center py-12 text-center">
                                            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/20">
                                                <CheckCircle2 className="h-8 w-8 text-primary" />
                                            </div>
                                            <h3 className="mt-6 text-lg font-semibold text-foreground">
                                                Request Submitted!
                                            </h3>
                                            <p className="mt-2 text-muted-foreground">
                                                Our enterprise team will contact you within 1 business day
                                                to discuss your fleet needs.
                                            </p>
                                            <Button
                                                variant="outline"
                                                className="mt-6"
                                                onClick={() => {
                                                    reset()
                                                    setIsSubmitted(false)
                                                }}
                                            >
                                                Submit Another Request
                                            </Button>
                                        </div>
                                    ) : (
                                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                                            <div className="grid gap-4 sm:grid-cols-2">
                                                <div className="space-y-2">
                                                    <Label htmlFor="name">Name</Label>
                                                    <Input id="name" placeholder="John Smith" {...register("name")} />
                                                    {errors.name && (
                                                        <p className="text-sm text-destructive">{errors.name.message}</p>
                                                    )}
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="phone">Phone Number</Label>
                                                    <Input id="phone" type="tel" placeholder="+1 (555) 000-0000" {...register("phone")} />
                                                    {errors.phone && (
                                                        <p className="text-sm text-destructive">{errors.phone.message}</p>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="grid gap-4 sm:grid-cols-2">
                                                <div className="space-y-2">
                                                    <Label htmlFor="email">Work Email</Label>
                                                    <Input id="email" type="email" placeholder="john@company.com" {...register("email")} />
                                                    {errors.email && (
                                                        <p className="text-sm text-destructive">{errors.email.message}</p>
                                                    )}
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="role">Your Role</Label>
                                                    <Input id="role" placeholder="Fleet Manager" {...register("role")} />
                                                    {errors.role && (
                                                        <p className="text-sm text-destructive">{errors.role.message}</p>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="company">Company Name</Label>
                                                <Input id="company" placeholder="Company Inc." {...register("company")} />
                                                {errors.company && (
                                                    <p className="text-sm text-destructive">{errors.company.message}</p>
                                                )}
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="fleetSize">Fleet Size</Label>
                                                <Select onValueChange={(value) => setValue("fleetSize", value)}>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select fleet size" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {fleetSizes.map((size) => (
                                                            <SelectItem key={size.value} value={size.value}>
                                                                {size.label}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                {errors.fleetSize && (
                                                    <p className="text-sm text-destructive">{errors.fleetSize.message}</p>
                                                )}
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="needs">Tell us about your needs</Label>
                                                <Textarea
                                                    id="needs"
                                                    placeholder="Describe your fleet operations, current challenges, and what you hope to achieve with Smart Tire Analyzer..."
                                                    rows={4}
                                                    {...register("needs")}
                                                />
                                                {errors.needs && (
                                                    <p className="text-sm text-destructive">{errors.needs.message}</p>
                                                )}
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="timeline">Implementation Timeline</Label>
                                                <Select onValueChange={(value) => setValue("timeline", value)}>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="When are you looking to start?" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="immediate">Immediately</SelectItem>
                                                        <SelectItem value="1-month">Within 1 month</SelectItem>
                                                        <SelectItem value="3-months">Within 3 months</SelectItem>
                                                        <SelectItem value="6-months">Within 6 months</SelectItem>
                                                        <SelectItem value="exploring">Just exploring options</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                {errors.timeline && (
                                                    <p className="text-sm text-destructive">{errors.timeline.message}</p>
                                                )}
                                            </div>

                                            <Button type="submit" className="w-full" disabled={isSubmitting}>
                                                {isSubmitting ? "Submitting..." : "Request a Demo"}
                                            </Button>

                                            <p className="text-center text-xs text-muted-foreground">
                                                By submitting, you agree to our Privacy Policy and Terms of Service.
                                            </p>
                                        </form>
                                    )}
                                </CardContent>
                            </Card>

                            {/* Testimonials & Stats */}
                            <div className="space-y-8">
                                {/* Stats */}
                                <div className="grid grid-cols-2 gap-4">
                                    <Card className="border-border/50 bg-card/50">
                                        <CardContent className="pt-6 text-center">
                                            <p className="text-4xl font-bold text-primary">500+</p>
                                            <p className="mt-1 text-sm text-muted-foreground">Enterprise Clients</p>
                                        </CardContent>
                                    </Card>
                                    <Card className="border-border/50 bg-card/50">
                                        <CardContent className="pt-6 text-center">
                                            <p className="text-4xl font-bold text-primary">2M+</p>
                                            <p className="mt-1 text-sm text-muted-foreground">Tires Monitored</p>
                                        </CardContent>
                                    </Card>
                                    <Card className="border-border/50 bg-card/50">
                                        <CardContent className="pt-6 text-center">
                                            <p className="text-4xl font-bold text-primary">35%</p>
                                            <p className="mt-1 text-sm text-muted-foreground">Avg. Cost Savings</p>
                                        </CardContent>
                                    </Card>
                                    <Card className="border-border/50 bg-card/50">
                                        <CardContent className="pt-6 text-center">
                                            <p className="text-4xl font-bold text-primary">99.9%</p>
                                            <p className="mt-1 text-sm text-muted-foreground">Uptime SLA</p>
                                        </CardContent>
                                    </Card>
                                </div>

                                {/* Testimonials */}
                                <div className="space-y-4">
                                    <h3 className="font-semibold text-foreground">Trusted by Industry Leaders</h3>
                                    {testimonials.map((testimonial) => (
                                        <Card key={testimonial.company} className="border-border/50 bg-card/50">
                                            <CardContent className="pt-6">
                                                <p className="text-muted-foreground">&ldquo;{testimonial.quote}&rdquo;</p>
                                                <div className="mt-4 flex items-center justify-between">
                                                    <div>
                                                        <p className="font-semibold text-foreground">{testimonial.author}</p>
                                                        <p className="text-sm text-muted-foreground">
                                                            {testimonial.role}, {testimonial.company}
                                                        </p>
                                                    </div>
                                                    <Badge variant="secondary">{testimonial.fleet}</Badge>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>

                                {/* Contact Info */}
                                <Card className="border-border/50 bg-primary/5">
                                    <CardContent className="pt-6">
                                        <h3 className="font-semibold text-foreground">Prefer to talk directly?</h3>
                                        <p className="mt-2 text-sm text-muted-foreground">
                                            Call our enterprise team at <span className="font-medium text-foreground">+1 (555) 987-6543</span>
                                        </p>
                                        <p className="mt-1 text-sm text-muted-foreground">
                                            or email <span className="font-medium text-foreground">enterprise@smarttire.ai</span>
                                        </p>
                                    </CardContent>
                                </Card>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    )
}
