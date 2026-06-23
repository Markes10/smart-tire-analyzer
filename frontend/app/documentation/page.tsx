"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
    FileText,
    Search,
    BookOpen,
    Zap,
    Camera,
    BarChart3,
    Users,
    Settings,
    Code,
    Shield,
    Smartphone,
    ArrowRight,
    ExternalLink
} from "lucide-react"

const categories = [
    {
        id: "getting-started",
        title: "Getting Started",
        icon: Zap,
        description: "Learn the basics and get up and running quickly",
        articles: [
            { title: "Quick Start Guide", time: "5 min read", popular: true },
            { title: "Creating Your Account", time: "3 min read" },
            { title: "Understanding the Dashboard", time: "4 min read" },
            { title: "Your First Tire Analysis", time: "6 min read", popular: true },
            { title: "Interpreting Results", time: "5 min read" },
        ]
    },
    {
        id: "image-capture",
        title: "Image Capture",
        icon: Camera,
        description: "Best practices for capturing tire images",
        articles: [
            { title: "Image Requirements", time: "4 min read", popular: true },
            { title: "Lighting Tips for Better Analysis", time: "3 min read" },
            { title: "Mobile Camera Best Practices", time: "4 min read" },
            { title: "Troubleshooting Poor Image Quality", time: "5 min read" },
            { title: "Batch Image Upload Guide", time: "6 min read" },
        ]
    },
    {
        id: "analysis",
        title: "Analysis & Reports",
        icon: BarChart3,
        description: "Understanding analysis results and reports",
        articles: [
            { title: "Health Score Explained", time: "5 min read", popular: true },
            { title: "Wear Pattern Types", time: "7 min read" },
            { title: "Tread Depth Measurements", time: "4 min read" },
            { title: "Generating PDF Reports", time: "3 min read" },
            { title: "Exporting Data to CSV", time: "3 min read" },
            { title: "Comparing Historical Data", time: "5 min read" },
        ]
    },
    {
        id: "fleet",
        title: "Fleet Management",
        icon: Users,
        description: "Managing multiple vehicles and team members",
        articles: [
            { title: "Setting Up Your Fleet", time: "6 min read" },
            { title: "Adding Vehicles", time: "4 min read" },
            { title: "Team Roles & Permissions", time: "5 min read" },
            { title: "Fleet Analytics Dashboard", time: "7 min read", popular: true },
            { title: "Maintenance Scheduling", time: "5 min read" },
            { title: "Cost Tracking & Budgeting", time: "6 min read" },
        ]
    },
    {
        id: "integrations",
        title: "Integrations",
        icon: Code,
        description: "Connect with your existing tools and systems",
        articles: [
            { title: "API Overview", time: "8 min read" },
            { title: "Authentication & API Keys", time: "5 min read" },
            { title: "Webhook Configuration", time: "6 min read" },
            { title: "Integrating with Fleet Software", time: "10 min read" },
            { title: "Zapier Integration", time: "4 min read" },
            { title: "Custom Integrations Guide", time: "12 min read" },
        ]
    },
    {
        id: "account",
        title: "Account & Settings",
        icon: Settings,
        description: "Manage your account and preferences",
        articles: [
            { title: "Account Settings Overview", time: "4 min read" },
            { title: "Updating Profile Information", time: "2 min read" },
            { title: "Notification Preferences", time: "3 min read" },
            { title: "Billing & Subscription", time: "4 min read" },
            { title: "Changing Your Plan", time: "3 min read" },
        ]
    },
    {
        id: "security",
        title: "Security & Privacy",
        icon: Shield,
        description: "Keeping your data safe and secure",
        articles: [
            { title: "Security Best Practices", time: "5 min read" },
            { title: "Two-Factor Authentication", time: "3 min read" },
            { title: "Data Encryption", time: "4 min read" },
            { title: "GDPR Compliance", time: "6 min read" },
            { title: "Data Retention Policy", time: "4 min read" },
        ]
    },
    {
        id: "mobile",
        title: "Mobile App",
        icon: Smartphone,
        description: "Using Smart Tire Analyzer on mobile devices",
        articles: [
            { title: "iOS App Guide", time: "5 min read" },
            { title: "Android App Guide", time: "5 min read" },
            { title: "Offline Mode", time: "4 min read" },
            { title: "Push Notifications", time: "3 min read" },
            { title: "Mobile Troubleshooting", time: "6 min read" },
        ]
    },
]

const popularArticles = [
    { title: "Quick Start Guide", category: "Getting Started", time: "5 min read" },
    { title: "Image Requirements", category: "Image Capture", time: "4 min read" },
    { title: "Health Score Explained", category: "Analysis & Reports", time: "5 min read" },
    { title: "Your First Tire Analysis", category: "Getting Started", time: "6 min read" },
    { title: "Fleet Analytics Dashboard", category: "Fleet Management", time: "7 min read" },
]

export default function DocumentationPage() {
    const [searchQuery, setSearchQuery] = useState("")
    const [activeCategory, setActiveCategory] = useState("getting-started")

    const filteredCategories = categories.filter(category =>
        category.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        category.articles.some(article =>
            article.title.toLowerCase().includes(searchQuery.toLowerCase())
        )
    )

    return (
        <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1 pt-16">
                {/* Hero Section */}
                <section className="border-b border-border/50 bg-muted/30 py-16">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <div className="mx-auto max-w-2xl text-center">
                            <div className="flex justify-center">
                                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
                                    <FileText className="h-7 w-7 text-primary" />
                                </div>
                            </div>
                            <h1 className="mt-6 text-4xl font-bold tracking-tight text-foreground">
                                Documentation
                            </h1>
                            <p className="mt-4 text-lg text-muted-foreground">
                                Everything you need to master Smart Tire Analyzer
                            </p>

                            {/* Search */}
                            <div className="relative mt-8">
                                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Search documentation..."
                                    className="h-12 pl-12 pr-4"
                                />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Main Content */}
                <section className="py-12">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <Tabs value={activeCategory} onValueChange={setActiveCategory}>
                            <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
                                {/* Sidebar */}
                                <aside className="space-y-6">
                                    {/* Quick Links */}
                                    <Card className="border-border/50 bg-card/50">
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-sm font-medium">Quick Links</CardTitle>
                                        </CardHeader>
                                        <CardContent className="space-y-2">
                                            <a href="/api-docs" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                                                <Code className="h-4 w-4" />
                                                API Reference
                                                <ExternalLink className="ml-auto h-3 w-3" />
                                            </a>
                                            <a href="/live-chat" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                                                <Zap className="h-4 w-4" />
                                                Live Support
                                            </a>
                                            <a href="/technical-support" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                                                <BookOpen className="h-4 w-4" />
                                                Submit Ticket
                                            </a>
                                        </CardContent>
                                    </Card>

                                    {/* Category Navigation */}
                                    <TabsList className="flex h-auto flex-col items-stretch bg-transparent p-0">
                                        {categories.map((category) => (
                                            <TabsTrigger
                                                key={category.id}
                                                value={category.id}
                                                className="justify-start gap-3 px-3 py-2.5 text-left data-[state=active]:bg-muted"
                                            >
                                                <category.icon className="h-4 w-4" />
                                                {category.title}
                                            </TabsTrigger>
                                        ))}
                                    </TabsList>
                                </aside>

                                {/* Main Content Area */}
                                <div>
                                    {searchQuery ? (
                                        // Search Results
                                        <div className="space-y-6">
                                            <h2 className="text-xl font-semibold text-foreground">
                                                Search Results for &ldquo;{searchQuery}&rdquo;
                                            </h2>
                                            {filteredCategories.length > 0 ? (
                                                filteredCategories.map((category) => {
                                                    const matchingArticles = category.articles.filter(article =>
                                                        article.title.toLowerCase().includes(searchQuery.toLowerCase())
                                                    )
                                                    if (matchingArticles.length === 0 && !category.title.toLowerCase().includes(searchQuery.toLowerCase())) {
                                                        return null
                                                    }
                                                    return (
                                                        <Card key={category.id} className="border-border/50 bg-card/50">
                                                            <CardHeader>
                                                                <div className="flex items-center gap-3">
                                                                    <category.icon className="h-5 w-5 text-primary" />
                                                                    <CardTitle className="text-lg">{category.title}</CardTitle>
                                                                </div>
                                                            </CardHeader>
                                                            <CardContent>
                                                                <div className="space-y-2">
                                                                    {(matchingArticles.length > 0 ? matchingArticles : category.articles).map((article) => (
                                                                        <a
                                                                            key={article.title}
                                                                            href={`/documentation#${category.id}-${article.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                                                                            className="flex items-center justify-between rounded-lg p-3 transition-colors hover:bg-muted/50"
                                                                        >
                                                                            <span className="font-medium text-foreground">{article.title}</span>
                                                                            <span className="text-sm text-muted-foreground">{article.time}</span>
                                                                        </a>
                                                                    ))}
                                                                </div>
                                                            </CardContent>
                                                        </Card>
                                                    )
                                                })
                                            ) : (
                                                <Card className="border-border/50 bg-card/50">
                                                    <CardContent className="py-12 text-center">
                                                        <p className="text-muted-foreground">No results found for &ldquo;{searchQuery}&rdquo;</p>
                                                        <Button variant="outline" className="mt-4" onClick={() => setSearchQuery("")}>
                                                            Clear Search
                                                        </Button>
                                                    </CardContent>
                                                </Card>
                                            )}
                                        </div>
                                    ) : (
                                        // Category Content
                                        <>
                                            {categories.map((category) => (
                                                <TabsContent key={category.id} value={category.id} className="mt-0">
                                                    <div className="space-y-6">
                                                        <div>
                                                            <div className="flex items-center gap-3">
                                                                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                                                    <category.icon className="h-5 w-5 text-primary" />
                                                                </div>
                                                                <div>
                                                                    <h2 className="text-2xl font-bold text-foreground">{category.title}</h2>
                                                                    <p className="text-muted-foreground">{category.description}</p>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="grid gap-3">
                                                            {category.articles.map((article) => (
                                                                <a
                                                                    key={article.title}
                                                                    href={`/documentation#${category.id}-${article.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                                                                    className="group flex items-center justify-between rounded-lg border border-border/50 bg-card/50 p-4 transition-colors hover:bg-muted/50"
                                                                >
                                                                    <div className="flex items-center gap-3">
                                                                        <BookOpen className="h-5 w-5 text-muted-foreground" />
                                                                        <span className="font-medium text-foreground">{article.title}</span>
                                                                        {article.popular && (
                                                                            <Badge variant="secondary" className="text-xs">Popular</Badge>
                                                                        )}
                                                                    </div>
                                                                    <div className="flex items-center gap-3">
                                                                        <span className="text-sm text-muted-foreground">{article.time}</span>
                                                                        <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                                                                    </div>
                                                                </a>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </TabsContent>
                                            ))}
                                        </>
                                    )}

                                    {/* Popular Articles */}
                                    {!searchQuery && (
                                        <Card className="mt-8 border-border/50 bg-primary/5">
                                            <CardHeader>
                                                <CardTitle className="text-lg">Popular Articles</CardTitle>
                                                <CardDescription>Most viewed documentation</CardDescription>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="grid gap-3 sm:grid-cols-2">
                                                    {popularArticles.map((article) => (
                                                        <a
                                                            key={article.title}
                                                            href={`/documentation#popular-${article.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                                                            className="flex flex-col rounded-lg border border-border/50 bg-background p-3 transition-colors hover:bg-muted/50"
                                                        >
                                                            <span className="font-medium text-foreground">{article.title}</span>
                                                            <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                                                                <span>{article.category}</span>
                                                                <span>&bull;</span>
                                                                <span>{article.time}</span>
                                                            </div>
                                                        </a>
                                                    ))}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )}
                                </div>
                            </div>
                        </Tabs>
                    </div>
                </section>

                {/* Help CTA */}
                <section className="border-t border-border/50 py-12">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <Card className="border-border/50 bg-card/50">
                            <CardContent className="flex flex-col items-center justify-between gap-6 py-8 sm:flex-row">
                                <div>
                                    <h3 className="text-lg font-semibold text-foreground">
                                        Can&apos;t find what you&apos;re looking for?
                                    </h3>
                                    <p className="mt-1 text-muted-foreground">
                                        Our support team is ready to help you
                                    </p>
                                </div>
                                <div className="flex gap-3">
                                    <Button variant="outline" asChild>
                                        <a href="/technical-support">Submit Ticket</a>
                                    </Button>
                                    <Button asChild>
                                        <a href="/live-chat">Start Live Chat</a>
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    )
}
