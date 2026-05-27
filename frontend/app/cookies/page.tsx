"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

const lastUpdated = "May 1, 2026"

const cookieCategories = [
  {
    id: "essential",
    title: "Essential Cookies",
    description: "These cookies are necessary for the website to function and cannot be switched off. They are usually set in response to actions you take such as setting privacy preferences, logging in, or filling in forms.",
    required: true,
    examples: ["Session management", "Authentication", "Security tokens", "Load balancing"],
  },
  {
    id: "functional",
    title: "Functional Cookies",
    description: "These cookies enable enhanced functionality and personalization, such as remembering your preferences and settings. They may be set by us or by third-party providers whose services we use.",
    required: false,
    examples: ["Language preferences", "Theme settings", "Recently viewed items", "Analysis history"],
  },
  {
    id: "analytics",
    title: "Analytics Cookies",
    description: "These cookies help us understand how visitors interact with our website by collecting and reporting information anonymously. This helps us improve our Service.",
    required: false,
    examples: ["Page views", "User journeys", "Feature usage", "Performance metrics"],
  },
  {
    id: "marketing",
    title: "Marketing Cookies",
    description: "These cookies may be set by our advertising partners to build a profile of your interests and show you relevant ads on other sites. They do not directly store personal information.",
    required: false,
    examples: ["Ad targeting", "Campaign tracking", "Cross-site tracking", "Remarketing"],
  },
]

const sections = [
  {
    title: "What Are Cookies?",
    content: `Cookies are small text files that are placed on your computer or mobile device when you visit a website. They are widely used to make websites work more efficiently, provide information to website owners, and enhance your browsing experience.

Cookies can be "persistent" (remaining on your device until they expire or you delete them) or "session" cookies (deleted when you close your browser).`,
  },
  {
    title: "How We Use Cookies",
    content: `Smart Tire Analyzer uses cookies and similar technologies for several purposes:

• To keep you signed in to your account
• To remember your preferences and settings
• To understand how you use our Service
• To improve our products and features
• To provide personalized content and recommendations
• To measure the effectiveness of our marketing campaigns`,
  },
  {
    title: "Third-Party Cookies",
    content: `Some cookies on our website are placed by third-party services that appear on our pages. We use the following third-party services:

• Google Analytics - For understanding website usage
• Stripe - For processing payments securely
• Intercom - For customer support chat
• Google Maps - For location-based features

These third parties have their own privacy policies governing the use of cookies.`,
  },
  {
    title: "Your Cookie Choices",
    content: `You have several options for managing cookies:

Browser Settings: Most browsers allow you to refuse or delete cookies. The method varies by browser, so check your browser's help documentation.

Our Cookie Settings: Use the preferences panel on this page to manage non-essential cookies on our Service.

Opt-Out Links: You can opt out of certain third-party cookies through industry opt-out mechanisms like the Digital Advertising Alliance or Network Advertising Initiative.

Note that disabling certain cookies may impact the functionality of our Service.`,
  },
  {
    title: "Updates to This Policy",
    content: `We may update this Cookie Policy from time to time to reflect changes in our practices or for legal, regulatory, or operational reasons. When we make changes, we will update the "Last updated" date at the top of this page.`,
  },
  {
    title: "Contact Us",
    content: `If you have questions about our use of cookies, please contact us at privacy@smarttire.ai or write to: Smart Tire Analyzer, 123 Innovation Drive, San Francisco, CA 94105.`,
  },
]

export default function CookiesPage() {
  const [preferences, setPreferences] = useState({
    essential: true,
    functional: true,
    analytics: true,
    marketing: false,
  })
  const [saved, setSaved] = useState(false)

  const handleToggle = (id: string) => {
    if (id === "essential") return
    setPreferences(prev => ({ ...prev, [id]: !prev[id as keyof typeof prev] }))
    setSaved(false)
  }

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleAcceptAll = () => {
    setPreferences({
      essential: true,
      functional: true,
      analytics: true,
      marketing: true,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <article className="py-24">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
            <header className="mb-12">
              <h1 className="text-4xl font-bold tracking-tight text-foreground">
                Cookie Policy
              </h1>
              <p className="mt-4 text-muted-foreground">
                Last updated: {lastUpdated}
              </p>
              <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
                This Cookie Policy explains how Smart Tire Analyzer uses cookies and similar 
                technologies to recognize you when you visit our website and use our services.
              </p>
            </header>

            {/* Cookie Preferences */}
            <Card className="mb-12 border-border/50 bg-card/50">
              <CardHeader>
                <CardTitle>Cookie Preferences</CardTitle>
                <CardDescription>
                  Manage your cookie preferences below. Essential cookies cannot be disabled 
                  as they are required for the website to function properly.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {cookieCategories.map((category) => (
                  <div key={category.id} className="flex items-start justify-between gap-4 rounded-lg border border-border/50 p-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Label htmlFor={category.id} className="font-semibold text-foreground">
                          {category.title}
                        </Label>
                        {category.required && (
                          <span className="text-xs text-muted-foreground">(Required)</span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {category.description}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {category.examples.map((example) => (
                          <span 
                            key={example}
                            className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                          >
                            {example}
                          </span>
                        ))}
                      </div>
                    </div>
                    <Switch
                      id={category.id}
                      checked={preferences[category.id as keyof typeof preferences]}
                      onCheckedChange={() => handleToggle(category.id)}
                      disabled={category.required}
                    />
                  </div>
                ))}
                <div className="flex gap-3">
                  <Button onClick={handleSave} className="flex-1">
                    {saved ? "Preferences Saved!" : "Save Preferences"}
                  </Button>
                  <Button onClick={handleAcceptAll} variant="outline">
                    Accept All
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Policy Sections */}
            <div className="space-y-12">
              {sections.map((section, index) => (
                <section key={section.title}>
                  <h2 className="text-2xl font-bold text-foreground">
                    {index + 1}. {section.title}
                  </h2>
                  <div className="mt-4 whitespace-pre-line leading-relaxed text-muted-foreground">
                    {section.content}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </article>
      </main>
      <Footer />
    </div>
  )
}
