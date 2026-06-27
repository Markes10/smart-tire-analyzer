import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ApiKeysForm } from '../api-keys-form'

describe('ApiKeysForm', () => {
  const defaultProps = {
    onSave: vi.fn(),
    saving: false,
  }

  it('renders all API key input fields', () => {
    render(<ApiKeysForm {...defaultProps} />)

    expect(screen.getByPlaceholderText('AIzaSy...')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('MLY|...')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('abc123...')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('123456-abc.apps.googleusercontent.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('GOCSPX-...')).toBeInTheDocument()

    expect(screen.getByText('API Keys — Bring Your Own')).toBeInTheDocument()
  })

  it('shows/hides secret key fields when toggling visibility', () => {
    render(<ApiKeysForm {...defaultProps} />)

    const geminiInput = screen.getByPlaceholderText('AIzaSy...')
    expect(geminiInput).toHaveAttribute('type', 'password')

    const toggleButtons = screen.getAllByRole('button')
    const eyeToggle = toggleButtons.find(btn =>
      btn.innerHTML.includes('lucide-eye') || btn.querySelector('svg')
    )
    expect(eyeToggle).toBeDefined()

    fireEvent.click(eyeToggle!)
    expect(screen.getByPlaceholderText('AIzaSy...')).toHaveAttribute('type', 'text')

    fireEvent.click(eyeToggle!)
    expect(screen.getByPlaceholderText('AIzaSy...')).toHaveAttribute('type', 'password')
  })

  it('calls onSave with entered keys when save button is clicked', () => {
    const onSave = vi.fn()
    render(<ApiKeysForm {...defaultProps} onSave={onSave} />)

    fireEvent.change(screen.getByPlaceholderText('AIzaSy...'), { target: { value: 'AIzaSyTest123' } })
    fireEvent.change(screen.getByPlaceholderText('MLY|...'), { target: { value: 'MLY|test-token' } })

    const button = screen.getByText('Update API Keys')
    fireEvent.click(button)

    expect(onSave).toHaveBeenCalledWith({
      gemini: 'AIzaSyTest123',
      mapillary: 'MLY|test-token',
    })
  })

  it('shows destructive alert when Gemini key is missing', () => {
    render(<ApiKeysForm {...defaultProps} />)

    expect(screen.getByText(/At minimum, a Gemini API key is needed/)).toBeInTheDocument()
  })

  it('hides Gemini warning when a key is provided', () => {
    render(<ApiKeysForm {...defaultProps} initialKeys={{ gemini: 'AIzaSyTest' }} />)

    expect(screen.queryByText(/At minimum, a Gemini API key is needed/)).not.toBeInTheDocument()
  })

  it('shows configured count when keys are present', () => {
    render(<ApiKeysForm {...defaultProps} initialKeys={{ gemini: 'key1', mapillary: 'key2' }} />)

    expect(screen.getByText('2 of 4 API keys configured')).toBeInTheDocument()
  })

  it('shows Update button text when keys exist', () => {
    render(<ApiKeysForm {...defaultProps} initialKeys={{ gemini: 'key1' }} />)

    expect(screen.getByText('Update API Keys')).toBeInTheDocument()
  })

  it('disables save button when saving is true', () => {
    render(<ApiKeysForm {...defaultProps} saving={true} />)

    expect(screen.getByText('Saving…')).toBeInTheDocument()
  })
})
