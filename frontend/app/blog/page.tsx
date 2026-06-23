"use client"

import { useState } from "react"
import Link from "next/link"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowRight } from "lucide-react"

const featuredPost = {
  title: "How AI is Revolutionizing Tire Safety: A Deep Dive into Our Multi-Model Architecture",
  description: "Explore the cutting-edge AI technology behind Smart Tire Analyzer, including our CNN, Transformer, and RNN ensemble approach to tire health prediction.",
  category: "Technology",
  date: "May 5, 2026",
  readTime: "8 min read",
  slug: "ai-revolutionizing-tire-safety",
}

const posts = [
  {
    title: "Understanding Tire Wear Patterns: What They Mean for Your Safety",
    description: "Learn to identify the 7 common tire wear patterns and what each indicates about your vehicle's alignment, inflation, and driving habits.",
    category: "Education",
    date: "May 1, 2026",
    readTime: "5 min read",
    slug: "understanding-tire-wear-patterns",
  },
  {
    title: "Fleet Management Best Practices: Reducing Costs with Predictive Maintenance",
    description: "How fleet managers are using AI-powered tire analysis to reduce maintenance costs by up to 30% while improving safety compliance.",
    category: "Fleet",
    date: "April 28, 2026",
    readTime: "6 min read",
    slug: "fleet-management-best-practices",
  },
  {
    title: "The Science Behind Tread Depth Measurement: From Manual to AI",
    description: "A technical look at how tire tread depth is measured, from traditional penny tests to our computer vision approach.",
    category: "Technology",
    date: "April 22, 2026",
    readTime: "7 min read",
    slug: "science-behind-tread-depth",
  },
  {
    title: "Seasonal Tire Care: Preparing Your Tires for Summer",
    description: "Essential tips for maintaining optimal tire performance during hot weather, including inflation adjustments and wear monitoring.",
    category: "Tips",
    date: "April 15, 2026",
    readTime: "4 min read",
    slug: "seasonal-tire-care-summer",
  },
  {
    title: "Case Study: How ABC Logistics Saved $2M with Smart Tire Analyzer",
    description: "A detailed look at how a major logistics company implemented our fleet solution and achieved significant cost savings.",
    category: "Case Study",
    date: "April 10, 2026",
    readTime: "6 min read",
    slug: "case-study-abc-logistics",
  },
  {
    title: "Introducing Continuous Learning: How Your Feedback Makes Us Smarter",
    description: "Learn about our self-correcting AI system that improves prediction accuracy through user feedback and automated retraining.",
    category: "Product",
    date: "April 5, 2026",
    readTime: "5 min read",
    slug: "introducing-continuous-learning",
  },
]

const categories = ["All", "Technology", "Education", "Fleet", "Tips", "Case Study", "Product"]

export default function BlogPage() {
  const [activeCategory, setActiveCategory] = useState("All")

  const filteredPosts = activeCategory === "All"
    ? posts
    : posts.filter(post => post.category === activeCategory)

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />

      <main className="flex-1 pt-24 pb-16">
        {/* Hero Section */}
        <section className="border-b border-border/50">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16">
            <div className="text-center">
              <h1 className="text-4xl font-bold text-foreground">Smart Tire Insights</h1>
              <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
                Expert articles, tips, and industry insights to help you maintain optimal tire health and vehicle safety.
              </p>
            </div>
          </div>
        </section>

        {/* Featured Post */}
        <section className="border-b border-border/50 py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 className="text-2xl font-bold text-foreground mb-8">Featured Article</h2>
            <Link href={`/blog/${featuredPost.slug}`}>
              <Card className="border-border/50 bg-card/50 hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary">{featuredPost.category}</Badge>
                    <span className="text-sm text-muted-foreground">{featuredPost.date}</span>
                  </div>
                  <CardTitle className="text-2xl">{featuredPost.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base mb-4">{featuredPost.description}</CardDescription>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{featuredPost.readTime}</span>
                    <div className="flex items-center gap-2 text-primary font-medium">
                      Read More
                      <ArrowRight className="h-4 w-4" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </section>

        {/* Category Filter */}
        <section className="border-b border-border/50 py-8 sticky top-20 bg-background/80 backdrop-blur-sm z-40">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {categories.map((category) => (
                <button
                  key={category}
                  type="button"
                  onClick={() => setActiveCategory(category)}
                  className={`whitespace-nowrap px-4 py-2 rounded-full font-medium text-sm transition-all ${activeCategory === category
                      ? "bg-primary text-primary-foreground"
                      : "border border-border/50 text-muted-foreground hover:text-foreground hover:border-border"
                    }`}
                  aria-pressed={activeCategory === category}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Blog Posts Grid */}
        <section className="py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {filteredPosts.length > 0 ? (
              <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                {filteredPosts.map((post) => (
                  <Link key={post.slug} href={`/blog/${post.slug}`}>
                    <Card className="border-border/50 bg-card/50 h-full hover:shadow-md transition-shadow cursor-pointer">
                      <CardHeader>
                        <div className="flex items-center justify-between mb-3">
                          <Badge variant="outline" className="text-xs">{post.category}</Badge>
                          <span className="text-xs text-muted-foreground">{post.date}</span>
                        </div>
                        <CardTitle className="line-clamp-2">{post.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="flex flex-col justify-between h-full">
                        <CardDescription className="line-clamp-3 mb-4">{post.description}</CardDescription>
                        <div className="flex items-center justify-between pt-4 border-t border-border/30">
                          <span className="text-xs text-muted-foreground">{post.readTime}</span>
                          <ArrowRight className="h-4 w-4 text-primary" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No articles found in this category. Try another filter.</p>
              </div>
            )}
          </div>
        </section>

        {/* Newsletter CTA */}
        <section className="border-t border-border/50 py-16 bg-muted/30">
          <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-2xl font-bold text-foreground mb-4">Stay Updated</h2>
            <p className="text-muted-foreground mb-6">
              Subscribe to our newsletter for the latest tire maintenance tips and industry insights.
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
