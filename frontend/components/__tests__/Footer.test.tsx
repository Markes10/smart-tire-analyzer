import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

vi.mock('next/link', () => {
  return {
    __esModule: true,
    default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => {
      return <a href={href} {...props}>{children}</a>
    },
  }
})

import { Footer } from '../footer'

describe('Footer', () => {
  it('renders brand name and tagline', () => {
    render(<Footer />)

    expect(screen.getByText('Smart Tire')).toBeInTheDocument()
    expect(screen.getByText(/AI-powered tire health analysis/)).toBeInTheDocument()
  })

  it('renders Product section links', () => {
    render(<Footer />)

    expect(screen.getByText('Product')).toBeInTheDocument()
    expect(screen.getByText('Features')).toBeInTheDocument()
    expect(screen.getByText('How It Works')).toBeInTheDocument()
    expect(screen.getByText('Fleet')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('API')).toBeInTheDocument()
  })

  it('renders Company section links', () => {
    render(<Footer />)

    expect(screen.getByText('Company')).toBeInTheDocument()
    expect(screen.getByText('About')).toBeInTheDocument()
    expect(screen.getByText('Blog')).toBeInTheDocument()
    expect(screen.getByText('Contact')).toBeInTheDocument()
  })

  it('renders Legal section links', () => {
    render(<Footer />)

    expect(screen.getByText('Legal')).toBeInTheDocument()
    expect(screen.getByText('Privacy')).toBeInTheDocument()
    expect(screen.getByText('Terms')).toBeInTheDocument()
    expect(screen.getByText('Cookies')).toBeInTheDocument()
  })

  it('renders Support section links', () => {
    render(<Footer />)

    expect(screen.getByText('Support')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Feedback')).toBeInTheDocument()
  })

  it('renders links with correct href values', () => {
    render(<Footer />)

    const featureLinks = screen.getAllByRole('link')
    const features = featureLinks.find(l => l.textContent === 'Features')
    expect(features).toHaveAttribute('href', '/')

    const fleet = featureLinks.find(l => l.textContent === 'Fleet')
    expect(fleet).toHaveAttribute('href', '/fleet')

    const dashboard = featureLinks.find(l => l.textContent === 'Dashboard')
    expect(dashboard).toHaveAttribute('href', '/dashboard')

    const api = featureLinks.find(l => l.textContent === 'API')
    expect(api).toHaveAttribute('href', '/api-docs')

    const about = featureLinks.find(l => l.textContent === 'About')
    expect(about).toHaveAttribute('href', '/about')

    const privacy = featureLinks.find(l => l.textContent === 'Privacy')
    expect(privacy).toHaveAttribute('href', '/privacy')
  })

  it('renders copyright notice', () => {
    render(<Footer />)

    expect(screen.getByText(/2026 Smart Tire Analyzer/)).toBeInTheDocument()
  })
})
