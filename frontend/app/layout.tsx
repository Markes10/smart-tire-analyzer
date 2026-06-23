import { Analytics } from '@vercel/analytics/next'
import './globals.css'
import type { Metadata } from 'next'
import AuthWrapper from '@/components/AuthWrapper'

export const metadata: Metadata = {
  title: 'Smart Tire Analyzer - AI-Powered Tire Health Assessment',
  description: 'Real-time tire health analysis, predictive maintenance, and driving safety recommendations powered by advanced AI.',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-background">
      <body className="font-sans antialiased" suppressHydrationWarning>
        <AuthWrapper>{children}</AuthWrapper>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  );
}
