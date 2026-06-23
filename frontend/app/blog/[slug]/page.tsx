"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Calendar, Clock, User, Share2 } from "lucide-react"

interface BlogPost {
    title: string
    category: string
    date: string
    readTime: string
    author: string
    excerpt: string
    content: string
}

const blogPosts: { [key: string]: BlogPost } = {
    "understanding-tire-wear-patterns": {
        title: "Understanding Tire Wear Patterns: What They Mean for Your Safety",
        category: "Education",
        date: "May 1, 2026",
        readTime: "5 min read",
        author: "Dr. Sarah Chen",
        excerpt: "Learn to identify the 7 common tire wear patterns and what each indicates about your vehicle's alignment, inflation, and driving habits.",
        content: `
      <h2>Why It Matters</h2>
      <p>Uneven wear can indicate alignment, inflation, or load issues that compromise traction and braking. Understanding tire wear patterns is not just about extending the life of your tires—it is a critical safety practice. Worn or unevenly worn tires dramatically reduce your vehicle's ability to grip the road, particularly in wet or slippery conditions, increasing the risk of accidents.</p>

      <h2>Key Indicators of Tire Wear</h2>

      <h3>Cupping (Scalloped Dips)</h3>
      <p>Dip-like wear patterns that look like the tire has been scooped out indicate suspension problems or improper tire balance. This serious issue can lead to vibration, noise, and potential tire failure. Have your suspension and tires inspected immediately if you notice this pattern.</p>

      <h3>Feathered Edges</h3>
      <p>A sawtooth or scalloped wear pattern across the tire indicates toe misalignment. This is when the front of your wheels angle inward or outward excessively. This not only wastes tire life but also affects steering response and fuel efficiency, requiring professional wheel alignment.</p>

      <h3>Central Wear</h3>
      <p>When the center of the tire wears faster than the edges, it is typically caused by overinflation. The center of the tire bulges slightly, causing it to contact the road more firmly than the edges. Check your tire pressure regularly and maintain the manufacturer-recommended PSI.</p>

      <h2>Smart Tire Analyzer Role</h2>
      <p>Smart Tire Analyzer uses computer vision to quantify wear zones and flag safety risks instantly. Instead of manual inspections, the AI-powered system analyzes tire images to identify wear patterns that might be missed by the naked eye. The system categorizes wear types, measures progression, and provides actionable recommendations for maintenance before safety becomes compromised.</p>

      <h2>Taking Action</h2>
      <p>Start monitoring your tire wear monthly using a tire depth gauge. Maintain proper inflation, rotate tires every 5,000–7,000 miles, and schedule professional wheel alignments annually or whenever you notice steering problems. With Smart Tire Analyzer, you receive real-time insights and proactive maintenance alerts, transforming tire care from reactive to preventive.</p>

      <h2>Conclusion</h2>
      <p>Understanding tire wear patterns empowers you to maintain your vehicle better and drive safer. Do not ignore the signs your tires are showing you—they are literally the only thing between you and the road. Regular monitoring combined with AI-powered analysis provides the confidence that your tires are safe.</p>
    `,
    },
    "fleet-management-best-practices": {
        title: "Fleet Management Best Practices: Reducing Costs with Predictive Maintenance",
        category: "Fleet",
        date: "April 28, 2026",
        readTime: "6 min read",
        author: "James Rodriguez",
        excerpt: "How fleet managers are using AI-powered tire analysis to reduce maintenance costs by up to 30% while improving safety compliance.",
        content: `
      <h2>Predictive vs. Reactive: Anticipate Failures Before They Happen</h2>
      <p>Reactive maintenance means fixing problems after they occur—expensive emergency repairs and unexpected downtime. Predictive maintenance anticipates failures before they happen, cutting downtime by up to 30%. By leveraging AI-powered tire analysis, fleet managers can identify potential issues weeks before they become critical, allowing for planned maintenance that minimizes disruption and reduces overall costs.</p>

      <h2>Data-Driven Decisions</h2>
      <p>Smart fleet operations combine multiple data streams: tire telemetry, route analytics, and weather forecasts. This holistic approach provides a complete picture of tire health and maintenance needs. Instead of guessing when tires need replacement, data shows exactly which vehicles are approaching end-of-life. Combining tire telemetry with route analytics and weather forecasts enables precise, just-in-time maintenance scheduling that eliminates both premature replacements and dangerous delays.</p>

      <h2>Smart Tire Analyzer Advantage</h2>
      <p>Real-time wear scoring feeds directly into fleet dashboards for automated service scheduling. The system prioritizes maintenance based on safety risk and cost optimization. Fleet managers receive actionable insights: which vehicles need tire rotation, which need immediate replacement, and which can safely continue operating. This precision eliminates guesswork and transforms tire management from a reactive cost center into a proactive safety and efficiency program.</p>

      <h2>Key Cost Reduction Strategies</h2>

      <h3>Proactive Wear Monitoring</h3>
      <p>AI-powered systems analyze tire images and sensor data to track wear progression. Fleet managers receive alerts when tires approach end-of-life, allowing planned replacement rather than emergency roadside repairs. This approach extends tire life by 10–20% through optimized rotation schedules.</p>

      <h3>Alignment and Pressure Management</h3>
      <p>Improper wheel alignment and tire pressure are among the biggest causes of premature wear in fleets. Smart Tire Analyzer provides continuous monitoring and alerts, preventing costly misalignments from going undetected. Proper inflation alone can reduce fuel consumption by 3–5%.</p>

      <h2>Conclusion</h2>
      <p>Predictive tire maintenance is not just about saving money—it is about building a safer, more efficient operation. The data-driven approach transforms tire management into a competitive advantage. Fleet managers who embrace this technology gain market share through improved reliability and reduced operating costs.</p>
    `,
    },
    "science-behind-tread-depth": {
        title: "The Science Behind Tread Depth Measurement: From Manual to AI",
        category: "Technology",
        date: "April 22, 2026",
        readTime: "7 min read",
        author: "Dr. Michael Zhang",
        excerpt: "A technical look at how tire tread depth is measured, from traditional penny tests to our computer vision approach.",
        content: `
      <h2>Traditional Method: Physical Gauges, Prone to Human Error</h2>
      <p>For decades, tire technicians relied on physical tools and human judgment to measure tread depth. The industry-standard penny test—inserting a penny upside down into the tread to see if Lincoln's head is visible—remains widely used despite significant limitations. Physical depth gauges provide numeric measurements but suffer from human interpretation variability, inability to assess wear uniformity across the tire, missed detection of localized wear patterns, and time-consuming manual inspection processes.</p>

      <h2>The AI Approach: Multi-Model Pipeline</h2>
      <p>Smart Tire Analyzer employs a sophisticated multi-model pipeline that evaluates tread depth from standard smartphone images with less than 0.2 mm error margin—exceeding professional gauge accuracy. Our CNN, ViT, BiLSTM, and Fusion ANN architecture works together to ensure robust, reliable measurements across diverse tire conditions and lighting environments.</p>

      <h3>DenseNet-121 (CNN)</h3>
      <p>Extracts low-level texture features directly from tire surface images, identifying micro-patterns in the tread rubber that correlate with depth and wear stage.</p>

      <h3>ViT-B16 (Transformer)</h3>
      <p>Captures global spatial relationships across the entire tire image, understanding how wear patterns relate to each other and to the overall tire geometry.</p>

      <h3>BiLSTM (RNN)</h3>
      <p>Models sequential wear progression across a series of tire images over time, enabling trend detection and predictive wear forecasting.</p>

      <h2>Benefits: Faster, More Consistent, Scalable</h2>
      <p><strong>Faster Inspections:</strong> A tire analysis completes in under 200ms, enabling real-time assessment rather than scheduled inspections.</p>
      <p><strong>Consistent Rub-Out Detection:</strong> The system identifies when tires have reached the wear bars with 99.2% reliability, preventing unsafe conditions from going unnoticed.</p>
      <p><strong>Scalable Across Thousands of Vehicles:</strong> One technician with a smartphone can assess an entire fleet's tire health in a fraction of the time manual processes require.</p>

      <h2>Accuracy Metrics</h2>
      <p>Validation studies show 97.8% accuracy in distinguishing safe versus unsafe tread depths, with a sub-0.2 mm error margin across varied lighting conditions and consistent performance on different tire brands and models. These metrics exceed traditional gauge accuracy and eliminate human interpretation variability entirely.</p>

      <h2>Conclusion</h2>
      <p>The transition from manual to AI-based tread depth measurement represents a fundamental shift in tire safety assessment. This technology enables proactive maintenance, improves safety, and dramatically reduces the labor required for fleet tire management. The days of the penny test are numbered.</p>
    `,
    },
    "seasonal-tire-care-summer": {
        title: "Seasonal Tire Care: Preparing Your Tires for Summer",
        category: "Tips",
        date: "April 15, 2026",
        readTime: "4 min read",
        author: "Marcus Johnson",
        excerpt: "Essential tips for maintaining optimal tire performance during hot weather, including inflation adjustments and wear monitoring.",
        content: `
      <h2>Heat-Related Wear: Higher Temperatures Accelerate Rubber Degradation</h2>
      <p>Heat increases the speed of chemical breakdown in rubber compounds, reduces tire stiffness leading to increased rolling resistance, amplifies existing alignment problems, and accelerates wear progression. Summer tires typically wear 20–30% faster than in winter conditions, making proactive monitoring essential for both safety and cost management.</p>

      <h2>Pre-Summer Checklist</h2>

      <h3>Verify Tire Pressure</h3>
      <p>Check pressure when tires are cold (before driving or at least 3 hours after driving). For every 10°F increase in temperature, tire pressure rises approximately 1 PSI. Maintain the vehicle manufacturer's recommended PSI—found on the door jamb or in your owner's manual, not the maximum pressure listed on the tire itself. Overinflation reduces traction and accelerates center wear.</p>

      <h3>Inspect Tread Depth</h3>
      <p>Use a depth gauge to verify tread depth is at least 4/32 inches (3.2 mm) for adequate wet weather performance. The legal minimum is 2/32 inches, but safety experts recommend replacement at 4/32 inches. Do not wait until tread becomes critically low—especially heading into a hot season.</p>

      <h3>Rotate Tires</h3>
      <p>Tire rotation every 5,000–7,000 miles promotes even wear and extends overall tire life. Rotation is especially important before summer when accelerated wear begins. Check your vehicle manual for the correct rotation pattern, particularly for all-wheel drive vehicles.</p>

      <h3>Check for Sidewall Cracks</h3>
      <p>Inspect sidewalls for cracks, splits, or unusual bulges. Sidewall damage can lead to rapid air loss and dangerous blowouts. Heat accelerates damage progression, so any cracks discovered in spring should be addressed immediately before the hottest months arrive.</p>

      <h2>Smart Tire Analyzer Tip</h2>
      <p>Upload a quick photo of your tires; the system highlights heat-stress zones and recommends rotation timing. Smart Tire Analyzer identifies where tread is wearing fastest, predicts when replacement will be needed based on current wear rates, and flags alignment issues that heat tends to amplify. This intelligent analysis takes the guesswork out of summer tire care and provides a clear action plan before problems escalate.</p>

      <h2>Conclusion</h2>
      <p>Summer tire maintenance is about being proactive. Regular pressure checks, tread inspection, rotation, and heat-aware driving practices keep your tires safe through hot weather. Combine these habits with AI-powered monitoring for maximum peace of mind and tire longevity.</p>
    `,
    },
    "case-study-abc-logistics": {
        title: "Case Study: How ABC Logistics Saved $2M with Smart Tire Analyzer",
        category: "Case Study",
        date: "April 10, 2026",
        readTime: "6 min read",
        author: "Jennifer Martinez",
        excerpt: "A detailed look at how a major logistics company implemented our fleet solution and achieved significant cost savings.",
        content: `
      <h2>Background: 1,200-Vehicle Fleet, Frequent Tire-Related Delays</h2>
      <p>ABC Logistics operates a fleet of 1,200 commercial vehicles across North America, generating approximately 50 million miles annually. Managing tire maintenance for such a massive fleet was their biggest operational headache. Their existing system relied on manual inspections, fixed maintenance schedules, and reactive repairs when problems occurred. Annual tire-related costs exceeded $10.2M, with frequent roadside tire failures causing delivery delays, customer complaints, and emergency repair expenses.</p>

      <h2>Implementation</h2>

      <h3>Phase 1: Pilot Program (Months 1–2)</h3>
      <p>ABC Logistics started with 200 vehicles representing diverse routes, climates, and usage patterns. Smart Tire Analyzer was integrated into their existing fleet management software. Technicians received training on capturing tire images consistently using smartphones. Initial baseline data was collected to establish current tire health status and cost benchmarks.</p>

      <h3>Phase 2: Full Integration — Weekly Automated Scans</h3>
      <p>Following successful pilot results, Smart Tire Analyzer was deployed to the entire 1,200-vehicle fleet. Weekly automated scans were enabled, with tire images captured at routine maintenance visits. The system was connected to their dispatch software to trigger maintenance alerts when vehicles reached predetermined wear thresholds, enabling automated service scheduling across all routes and depots.</p>

      <h3>Phase 3: Optimization (Months 5–12)</h3>
      <p>Based on accumulated data, ABC Logistics refined their rotation schedules, adjusted replacement thresholds for different vehicle types, and optimized their parts inventory to match predicted demand.</p>

      <h2>Results</h2>

      <h3>$1.3M Saved on Premature Replacements</h3>
      <p>Smart Tire Analyzer identified that approximately 25% of tires were being replaced earlier than necessary. Predictive wear scoring allowed the team to extend tire service life safely, eliminating unnecessary early replacements while maintaining full safety compliance.</p>

      <h3>$0.7M Saved on Avoided Downtime</h3>
      <p>Roadside tire failures dropped by 62% year-over-year. Each avoided breakdown saved an average of $580 in emergency repair costs, lost driver time, and missed delivery penalties. The reduction in unplanned stops translated directly into improved on-time delivery rates and stronger customer satisfaction scores.</p>

      <h3>15% Reduction in Fuel Consumption Due to Optimal Tread</h3>
      <p>Maintaining optimal tread depth and proper inflation across the fleet delivered measurable fuel efficiency gains. Properly inflated tires with adequate tread generate less rolling resistance, reducing fuel burn. Across 50 million annual miles, this 15% improvement represented a substantial operational saving.</p>

      <h2>Conclusion</h2>
      <p>The ABC Logistics case demonstrates that AI-powered tire management delivers measurable, multi-dimensional returns. The $2M total saving in year one represented a 19x return on investment, with compounding benefits as the model continued to learn and improve. For fleet operators of any size, predictive tire maintenance is no longer optional—it is a competitive necessity.</p>
    `,
    },
    "introducing-continuous-learning": {
        title: "Introducing Continuous Learning: How User Feedback Makes Us Smarter",
        category: "Product",
        date: "April 5, 2026",
        readTime: "5 min read",
        author: "Dr. Aisha Patel",
        excerpt: "Learn about our self-correcting AI system that improves prediction accuracy through user feedback and automated retraining.",
        content: `
      <h2>Feedback Loop: Drivers Flag False Positives and Negatives via the Mobile App</h2>
      <p>Every prediction Smart Tire Analyzer makes is an opportunity to learn. When drivers or technicians encounter a result that does not match their real-world observation—whether a false alarm flagging a healthy tire as worn, or a missed detection of actual damage—they can report it directly through the mobile app in seconds. These corrections are not discarded; they become training data that makes the model smarter for every subsequent user.</p>

      <h2>Model Updates: Weekly Retraining</h2>
      <p>Incorporates new edge-case images, improving accuracy by 3–5% each cycle. Our automated retraining pipeline runs on a weekly schedule, ingesting validated feedback reports, newly labeled images from partner fleets, and synthetic data generated to cover underrepresented tire conditions. Each retraining cycle is evaluated against a held-out test set before deployment, ensuring that accuracy improves monotonically and that no regression is introduced.</p>

      <h2>Transparency: Versioned Model Releases with Changelogs</h2>
      <p>Visible to fleet managers, every model update is logged with a version number and a plain-language changelog describing what changed, which edge cases were addressed, and what accuracy improvements were measured. Fleet managers can compare predictions from different model versions on their own historical data, building confidence in the system and understanding exactly why recommendations may change over time.</p>

      <h2>Why This Matters</h2>
      <p>Traditional AI systems are trained once and deployed indefinitely, gradually becoming less accurate as the real world drifts from their training distribution. Smart Tire Analyzer avoids this decay through continuous learning. New tire models, new road surface types, new climate extremes, and new vehicle categories are all incorporated into the model as they are encountered, ensuring that accuracy improves rather than degrades over time.</p>

      <h2>Conclusion</h2>
      <p>Continuous learning transforms Smart Tire Analyzer from a static tool into a living system that grows more capable with every inspection performed. User feedback is not just welcomed—it is the engine that drives ongoing improvement. The result is a platform that gets better the more it is used, creating a virtuous cycle that benefits every driver and fleet manager on the network.</p>
    `,
    },
    "ai-revolutionizing-tire-safety": {
        title: "How AI is Revolutionizing Tire Safety: A Deep Dive into Our Multi-Model Architecture",
        category: "Technology",
        date: "May 5, 2026",
        readTime: "8 min read",
        author: "Dr. Sarah Chen",
        excerpt: "Explore the cutting-edge AI technology behind Smart Tire Analyzer, including our CNN, Transformer, and RNN ensemble approach to tire health prediction.",
        content: `
      <h2>Hybrid Design: Four Models Working as One</h2>
      <p>The core of Smart Tire Analyzer is a deep ensemble architecture that combines the complementary strengths of four distinct neural network families. No single model architecture can optimally capture all the information embedded in a tire image—texture, geometry, temporal progression, and global context each require a different inductive bias. Our hybrid design exploits this diversity to achieve accuracy and robustness that no single model can match.</p>

      <h3>DenseNet-121 (CNN) — Extracts Low-Level Texture Features</h3>
      <p>DenseNet-121 is a densely connected convolutional neural network that excels at capturing fine-grained surface textures. Applied to tire images, it identifies micro-patterns in the rubber surface—groove depth, rubber compound color shifts, hairline cracks, and early-stage cupping—that are invisible to the human eye at normal inspection distances. Its dense connectivity ensures that low-level features are preserved throughout the network and remain available to later fusion layers.</p>

      <h3>ViT-B16 (Transformer) — Captures Global Spatial Relationships</h3>
      <p>The Vision Transformer divides the tire image into a grid of patches and processes them using self-attention, enabling the model to reason about relationships between distant regions of the tire simultaneously. This global receptive field is critical for detecting asymmetric wear patterns—conditions where the interaction between the outer shoulder and the inner shoulder reveals alignment or loading problems that a purely local model would miss.</p>

      <h3>BiLSTM (RNN) — Models Sequential Wear Progression Across Tire Images</h3>
      <p>When multiple images of the same tire are available over time, the Bidirectional Long Short-Term Memory network models the temporal trajectory of wear. It learns that a tire that has progressed from 8 mm to 6 mm tread depth in three months is on a very different trajectory than one that made the same transition in twelve months, and adjusts its replacement timeline predictions accordingly.</p>

      <h3>Deep Dense Fusion Network (ANN) — Merges Outputs into a Single Safety Score</h3>
      <p>The Fusion ANN receives the feature vectors produced by the three upstream models and learns the optimal weighted combination for each type of prediction task. It produces the final safety score, wear classification, and replacement timeline estimate that are presented to the user. The fusion layer is retrained weekly as new feedback data arrives, continuously refining the weights assigned to each upstream model.</p>

      <h2>Advantages: Robust to Lighting Variance, Occlusions, and Different Tire Models</h2>
      <p>Individual models tend to fail in specific edge cases—CNNs struggle with unusual lighting, Transformers need sufficient image resolution, RNNs require historical data. The ensemble architecture degrades gracefully when one model encounters a difficult case, because the other models continue to provide signal. Extensive adversarial testing across 200+ tire brands, six continents, and simulated lighting conditions from direct sunlight to low-light smartphone captures confirms robust performance across all tested scenarios.</p>

      <h2>Outcome: State-of-the-Art Accuracy</h2>
      <p>The combined architecture achieves 97.8% predictive accuracy on our validation set, with real-time inference completing in under 200 ms per image on standard cloud hardware. This means that the time between a driver uploading a photo and receiving a detailed safety report is shorter than a typical web page load—making AI-powered tire analysis genuinely practical for daily use at scale.</p>

      <h2>Conclusion</h2>
      <p>The multi-model architecture is not just an engineering choice—it is a statement about the complexity of the problem. Tires are sophisticated mechanical systems operating in highly variable environments, and they deserve an AI system that matches that complexity. By combining the strengths of convolutional networks, transformers, recurrent networks, and learned fusion, Smart Tire Analyzer delivers the accuracy and reliability that real-world safety applications demand.</p>
    `,
    },
}

const categoryColors: { [key: string]: string } = {
    Technology: "bg-primary text-primary-foreground",
    Education: "bg-chart-2/20 text-chart-2",
    Fleet: "bg-chart-3/20 text-chart-3",
    Tips: "bg-warning/20 text-warning",
    "Case Study": "bg-chart-4/20 text-chart-4",
    Product: "bg-primary/20 text-primary",
}

function renderInlineContent(content: string) {
    return content.split(/(<strong>.*?<\/strong>)/g).map((part) => {
        const strongMatch = part.match(/^<strong>(.*?)<\/strong>$/)
        if (strongMatch) {
            return <strong key={`strong-${strongMatch[1]}`}>{strongMatch[1]}</strong>
        }
        return part
    })
}

function renderPostContent(content: string) {
    return Array.from(content.matchAll(/<(h2|h3|p)>([\s\S]*?)<\/\1>/g)).map((match) => {
        const tag = match[1]
        const text = match[2].trim()
        const key = `${tag}-${text.slice(0, 80)}`
        const children = renderInlineContent(text)

        if (tag === "h2") {
            return (
                <h2 key={key}>
                    {children}
                </h2>
            )
        }

        if (tag === "h3") {
            return (
                <h3 key={key}>
                    {children}
                </h3>
            )
        }

        return (
            <p key={key}>
                {children}
            </p>
        )
    })
}

function BlogPostContent({ content }: { content: string }) {
    return renderPostContent(content)
}

export default function BlogPostPage() {
    const params = useParams()
    const slug = params?.slug as string
    const post = blogPosts[slug]

    if (!post) {
        return (
            <div className="flex min-h-screen flex-col bg-background">
                <Header />
                <main className="flex-1 pt-24 pb-16">
                    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
                        <div className="py-20 text-center">
                            <h1 className="text-3xl font-bold text-foreground mb-4">Article Not Found</h1>
                            <p className="text-muted-foreground mb-8">The article you are looking for does not exist.</p>
                            <Button asChild>
                                <Link href="/blog">Back to Blog</Link>
                            </Button>
                        </div>
                    </div>
                </main>
                <Footer />
            </div>
        )
    }

    return (
        <div className="flex min-h-screen flex-col bg-background">
            <Header />

            <main className="flex-1 pt-24 pb-16">
                <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
                    {/* Back link */}
                    <div className="mb-8">
                        <Link
                            href="/blog"
                            className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                        >
                            <ArrowLeft className="h-4 w-4" />
                            Back to Blog
                        </Link>
                    </div>

                    {/* Article Header */}
                    <header className="mb-12">
                        <div className="flex items-center gap-3 mb-6 flex-wrap">
                            <Badge className={categoryColors[post.category] || "bg-secondary text-secondary-foreground"}>
                                {post.category}
                            </Badge>
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                <Calendar className="h-4 w-4" />
                                {post.date}
                            </div>
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                <Clock className="h-4 w-4" />
                                {post.readTime}
                            </div>
                        </div>

                        <h1 className="text-3xl font-bold text-balance text-foreground sm:text-4xl lg:text-5xl mb-6 leading-tight">
                            {post.title}
                        </h1>

                        <p className="text-xl text-muted-foreground leading-relaxed mb-8">
                            {post.excerpt}
                        </p>

                        <div className="flex items-center justify-between flex-wrap gap-4 border-t border-border/50 pt-6">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <User className="h-4 w-4" />
                                <span className="font-medium text-foreground">{post.author}</span>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                className="gap-2"
                                onClick={() => navigator.clipboard.writeText(window.location.href)}
                            >
                                <Share2 className="h-4 w-4" />
                                Share
                            </Button>
                        </div>
                    </header>

                    {/* Article Content */}
                    <article className="prose max-w-none">
                        <BlogPostContent content={post.content} />
                    </article>

                    {/* CTA Card */}
                    <div className="mt-16 border-t border-border/50 pt-16">
                        <Card className="border-primary/20 bg-linear-to-br from-primary/5 to-primary/10">
                            <CardHeader>
                                <CardTitle className="text-2xl">Try Smart Tire Analyzer</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-muted-foreground mb-6 leading-relaxed">
                                    Put the insights from this article into action. Upload a photo of your tire and get
                                    an AI-powered health assessment in under 2 seconds.
                                </p>
                                <div className="flex flex-col gap-3 sm:flex-row">
                                    <Button asChild>
                                        <Link href="/analyze">Start Free Analysis</Link>
                                    </Button>
                                    <Button variant="outline" asChild>
                                        <Link href="/blog">Read More Articles</Link>
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    )
}
