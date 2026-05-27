import { Header } from "@/components/header"
import { Footer } from "@/components/footer"

const lastUpdated = "May 1, 2026"

const sections = [
  {
    title: "Information We Collect",
    content: [
      {
        subtitle: "Account Data",
        text: "Email address, name, organization, password hash — Create and manage your account, authenticate you, and communicate about the Service.",
      },
      {
        subtitle: "Device & Usage Data",
        text: "IP address, browser/OS, device type, timestamps, API request logs, error reports — Operate, secure, and improve the Service; detect abuse; perform analytics.",
      },
      {
        subtitle: "Uploaded Images & Sensor Data",
        text: "Tire side-wall photographs, metadata (e.g., geolocation if supplied) — Run AI analysis, generate reports, and improve model accuracy.",
      },
      {
        subtitle: "Cookies & Similar Technologies",
        text: "Session cookies, analytics pixels — Preserve session state, remember preferences, and gather aggregated usage statistics.",
      },
      {
        subtitle: "Optional Feedback",
        text: "Survey responses, support tickets — Enhance user experience and troubleshoot issues.",
      },
    ],
  },
  {
    title: "How We Use Your Information",
    content: [
      {
        subtitle: "Service Delivery",
        text: "Process images, generate predictions, and provide results to you.",
      },
      {
        subtitle: "Account Management",
        text: "Authenticate, maintain security settings, and send important account notifications.",
      },
      {
        subtitle: "Improvement & Research",
        text: "Aggregate anonymized data to train and refine our AI models.",
      },
      {
        subtitle: "Security & Fraud Prevention",
        text: "Monitor for suspicious activity, enforce rate limits, and protect against attacks.",
      },
      {
        subtitle: "Communications",
        text: "Respond to support requests, send security alerts, and share optional product updates (you may opt-out).",
      },
      {
        subtitle: "Compliance",
        text: "Meet legal obligations, enforce terms of service, and respond to legitimate governmental requests.",
      },
    ],
  },
  {
    title: "Information Sharing",
    content: [
      {
        subtitle: "Service Providers",
        text: "We share information with cloud hosting, email delivery, and analytics providers through Data Processing Agreements with limited access and encryption in transit and at rest.",
      },
      {
        subtitle: "Legal Authorities",
        text: "We comply with subpoenas, court orders, or other legal requirements. We only disclose required data and notify you when permitted.",
      },
      {
        subtitle: "Business Transfers",
        text: "If involved in a merger, acquisition, or sale of assets, your data is handled with confidentiality obligations as per this policy.",
      },
      {
        subtitle: "Aggregated & De-identified Data",
        text: "We may use anonymized data for research, public reports, and marketing purposes — no personally identifiable information is included.",
      },
      {
        subtitle: "Data Sales Policy",
        text: "We do not sell your personal data to third parties.",
      },
    ],
  },
  {
    title: "Data Security",
    content: [
      {
        subtitle: "Encryption",
        text: "TLS 1.3 for data in transit; AES-256 encryption at rest.",
      },
      {
        subtitle: "Access Controls",
        text: "Role-based access, multi-factor authentication for staff, least-privilege principle.",
      },
      {
        subtitle: "Monitoring",
        text: "Continuous intrusion detection, logging, and regular security audits.",
      },
      {
        subtitle: "Data Retention",
        text: "We retain personal data only as long as necessary for the purposes described. Tire images are deleted 30 days after analysis.",
      },
    ],
  },
  {
    title: "Your Rights and Choices",
    content: [
      {
        subtitle: "Access and Correction",
        text: "You can access, update, or correct your personal information through your account settings at any time.",
      },
      {
        subtitle: "Data Deletion",
        text: "You can request deletion of your account and associated data by contacting our support team. Some data may be retained as required by law or for legitimate business purposes.",
      },
      {
        subtitle: "Data Portability",
        text: "You can request a copy of your data in a machine-readable format through your account settings.",
      },
      {
        subtitle: "Opt-Out",
        text: "You can opt out of AI model training, promotional communications, and certain data collection through your account settings or by contacting us.",
      },
    ],
  },
  {
    title: "International Data Transfers",
    content: [
      {
        subtitle: "Cross-Border Transfers",
        text: "Your information may be transferred to and processed in countries other than your country of residence. We ensure appropriate safeguards are in place for such transfers, including standard contractual clauses.",
      },
    ],
  },
  {
    title: "Children's Privacy",
    content: [
      {
        subtitle: "Age Restrictions",
        text: "Our services are not intended for children under 16. We do not knowingly collect information from children under 16. If you believe we have collected information from a child, please contact us.",
      },
    ],
  },
  {
    title: "Changes to This Policy",
    content: [
      {
        subtitle: "Policy Updates",
        text: "We may update this Privacy Policy from time to time. We will notify you of significant changes by email or through a notice on our website. Your continued use of our services after changes take effect constitutes acceptance of the updated policy.",
      },
    ],
  },
  {
    title: "Contact Us",
    content: [
      {
        subtitle: "Questions or Concerns",
        text: "If you have questions about this Privacy Policy or our data practices, please contact us at privacy@smarttire.ai or write to us at: Smart Tire Analyzer, 123 Innovation Drive, San Francisco, CA 94105.",
      },
    ],
  },
]

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <article className="py-24">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
            <header className="mb-12">
              <h1 className="text-4xl font-bold tracking-tight text-foreground">
                Privacy Policy
              </h1>
              <p className="mt-4 text-muted-foreground">
                Last updated: {lastUpdated}
              </p>
              <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
                At Smart Tire Analyzer, we take your privacy seriously. This Privacy Policy explains
                how we collect, use, disclose, and safeguard your information when you use our
                tire analysis services.
              </p>
            </header>

            <div className="space-y-12">
              {sections.map((section, index) => (
                <section key={section.title}>
                  <h2 className="text-2xl font-bold text-foreground">
                    {index + 1}. {section.title}
                  </h2>
                  <div className="mt-6 space-y-6">
                    {section.content.map((item) => (
                      <div key={item.subtitle}>
                        <h3 className="font-semibold text-foreground">{item.subtitle}</h3>
                        <p className="mt-2 leading-relaxed text-muted-foreground">{item.text}</p>
                      </div>
                    ))}
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
