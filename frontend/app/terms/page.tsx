import { Header } from "@/components/header"
import { Footer } from "@/components/footer"

const lastUpdated = "May 1, 2026"

const sections = [
  {
    title: "Acceptance of Terms",
    content: `By accessing or using the Smart Tire Analyzer service (the "Service"), you (the "User") agree to be bound by these Terms of Service ("Terms") and our Privacy Policy. If you do not agree, you may not use the Service.`,
  },
  {
    title: "Description of Service",
    content: `Smart Tire Analyzer provides AI-driven analysis of tire side-wall images, predictive maintenance recommendations, and related reporting tools. The Service is offered on a subscription basis and may be accessed via a web interface, API, or desktop client.`,
  },
  {
    title: "User Accounts",
    content: `Registration: Users must create an account with a valid email address and a secure password.

Responsibility: You are responsible for all activity that occurs under your account and must keep your credentials confidential.

Eligibility: You must be at least 18 years old or have legal authority to bind your organization.`,
  },
  {
    title: "Acceptable Use",
    content: `You shall not:

• Upload unlawful, defamatory, or copyrighted material without permission.
• Attempt to reverse-engineer, decompile, or otherwise derive the underlying source code.
• Use the Service to harass, threaten, or discriminate against any person.
• Interfere with the Service's operation (e.g., DDoS attacks, scraping, or automated abuse).
• Violate any applicable laws or regulations.

Violations may result in immediate suspension or termination of your account.`,
  },
  {
    title: "Intellectual Property",
    content: `Ownership: All rights, title, and interest in the Service, including software, algorithms, trademarks, and documentation, are owned by Smart Tire Analyzer LLC ("we" or "the Company").

License: Subject to these Terms, we grant you a limited, non-exclusive, non-transferable, revocable license to use the Service solely for your internal business purposes.

User Content: By uploading images or data, you grant us a worldwide, royalty-free license to process, store, and display such content solely for providing the Service.`,
  },
  {
    title: "Disclaimer of Warranties",
    content: `The Service is provided "as is" and "as available" without warranties of any kind, whether express, implied, statutory, or otherwise, including without limitation:

• Merchantability, fitness for a particular purpose, and non-infringement.
• Accuracy, reliability, or completeness of AI predictions.
• Continuous, uninterrupted, or error-free operation.`,
  },
  {
    title: "Limitation of Liability",
    content: `To the maximum extent permitted by law, we shall not be liable for any:

• Direct, indirect, incidental, special, consequential, or punitive damages arising out of or related to your use of the Service.
• Loss of profits, revenue, data, or use.
• Liability exceeding the total amount you have paid us in the twelve (12) months preceding the claim.`,
  },
  {
    title: "Indemnification",
    content: `You agree to indemnify, defend, and hold harmless Smart Tire Analyzer LLC, its affiliates, officers, directors, employees, and agents from any claims, liabilities, damages, losses, or expenses (including reasonable attorneys' fees) arising out of:

• Your breach of these Terms.
• Your misuse of the Service or violation of any law.
• Any content you submit that infringes third-party rights.`,
  },
  {
    title: "Subscription and Payment",
    content: `Plans: Access to the Service is offered through tiered subscription plans (monthly, annual, or enterprise).

Billing: By subscribing, you authorize us to charge the payment method on file for the applicable fees and any taxes.

Refunds: All fees are non-refundable except as required by law or at our sole discretion.

Changes: We may modify pricing with at least 30 days' notice; existing subscriptions will continue under current terms until renewal.`,
  },
  {
    title: "Termination",
    content: `By You: You may terminate your account at any time via the account settings page.

By Us: We may suspend or terminate your access immediately for breach of these Terms, illegal activity, or at our sole discretion.

Effect: Upon termination, all licenses granted herein cease, and you must discontinue use of the Service. Outstanding fees become immediately due.`,
  },
  {
    title: "Governing Law",
    content: `These Terms shall be governed by and construed in accordance with the laws of the State of California, United States, without regard to its conflict-of-law principles. Any disputes shall be resolved exclusively in the state or federal courts located in San Francisco County, California.`,
  },
  {
    title: "Changes to Terms",
    content: `We may revise these Terms from time to time. When we do, we will:

• Post the revised Terms on the Service with a "Last Updated" date.
• Provide at least 30 days' advance notice for material changes.
• Continued use of the Service after such notice constitutes acceptance of the updated Terms.`,
  },
  {
    title: "Contact Information",
    content: `If you have questions about these Terms, please contact us at:

Smart Tire Analyzer LLC
Email: support@smarttireanalyzer.com
Address: 123 Innovation Way, San Francisco, CA 94107, USA

By using Smart Tire Analyzer, you acknowledge that you have read, understood, and agree to these Terms of Service.`,
  },
]

export default function TermsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <article className="py-24">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
            <header className="mb-12">
              <h1 className="text-4xl font-bold tracking-tight text-foreground">
                Terms of Service
              </h1>
              <p className="mt-4 text-muted-foreground">
                Last updated: {lastUpdated}
              </p>
              <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
                Please read these Terms of Service carefully before using Smart Tire Analyzer.
                These terms govern your access to and use of our tire analysis services.
              </p>
            </header>

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
