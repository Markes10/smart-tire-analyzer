import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: any) => <div data-testid="mock-dropdown">{children}</div>,
  DropdownMenuTrigger: ({ children }: any) => <div data-testid="mock-trigger">{children}</div>,
  DropdownMenuContent: ({ children }: any) => <div data-testid="mock-content">{children}</div>,
  DropdownMenuItem: ({ children, onClick }: any) => <button data-testid="mock-item" onClick={onClick}>{children}</button>,
  DropdownMenuSeparator: () => <div data-testid="mock-separator" />,
}))

vi.mock('@/components/theme-provider', () => ({
  useTheme: vi.fn(),
}))

import { useTheme } from '@/components/theme-provider'
import { ThemeToggle } from '../theme-toggle'

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useTheme as Mock).mockReturnValue({
      mode: 'dark',
      setMode: vi.fn(),
      resolvedMode: 'dark',
      setIsSettingsOpen: vi.fn(),
    })
  })

  it('renders the toggle button', () => {
    render(<ThemeToggle />)

    const button = screen.getByRole('button', { name: /toggle theme/i })
    expect(button).toBeInTheDocument()
  })

  it('shows Moon icon when resolvedMode is dark', () => {
    render(<ThemeToggle />)

    const button = screen.getByRole('button', { name: /toggle theme/i })
    expect(button.innerHTML).toContain('lucide-moon')
  })

  it('shows Sun icon when resolvedMode is light', () => {
    ;(useTheme as Mock).mockReturnValue({
      mode: 'light',
      setMode: vi.fn(),
      resolvedMode: 'light',
      setIsSettingsOpen: vi.fn(),
    })

    render(<ThemeToggle />)
    const button = screen.getByRole('button', { name: /toggle theme/i })
    expect(button.innerHTML).toContain('lucide-sun')
  })

  it('renders all theme options', () => {
    render(<ThemeToggle />)

    expect(screen.getByText('Light')).toBeInTheDocument()
    expect(screen.getByText('Dark')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
    expect(screen.getByText('Theme Settings')).toBeInTheDocument()
  })

  it('calls setMode("light") when Light is clicked', () => {
    const setMode = vi.fn()
    ;(useTheme as Mock).mockReturnValue({
      mode: 'dark',
      setMode,
      resolvedMode: 'dark',
      setIsSettingsOpen: vi.fn(),
    })

    render(<ThemeToggle />)

    fireEvent.click(screen.getByText('Light'))
    expect(setMode).toHaveBeenCalledWith('light')
  })

  it('calls setMode("dark") when Dark is clicked', () => {
    const setMode = vi.fn()
    ;(useTheme as Mock).mockReturnValue({
      mode: 'light',
      setMode,
      resolvedMode: 'light',
      setIsSettingsOpen: vi.fn(),
    })

    render(<ThemeToggle />)

    fireEvent.click(screen.getByText('Dark'))
    expect(setMode).toHaveBeenCalledWith('dark')
  })

  it('calls setMode("system") when System is clicked', () => {
    const setMode = vi.fn()
    ;(useTheme as Mock).mockReturnValue({
      mode: 'dark',
      setMode,
      resolvedMode: 'dark',
      setIsSettingsOpen: vi.fn(),
    })

    render(<ThemeToggle />)

    fireEvent.click(screen.getByText('System'))
    expect(setMode).toHaveBeenCalledWith('system')
  })

  it('calls setIsSettingsOpen when Theme Settings is clicked', () => {
    const setIsSettingsOpen = vi.fn()
    ;(useTheme as Mock).mockReturnValue({
      mode: 'dark',
      setMode: vi.fn(),
      resolvedMode: 'dark',
      setIsSettingsOpen,
    })

    render(<ThemeToggle />)

    fireEvent.click(screen.getByText('Theme Settings'))
    expect(setIsSettingsOpen).toHaveBeenCalledWith(true)
  })

  it('shows active indicator for current mode', () => {
    ;(useTheme as Mock).mockReturnValue({
      mode: 'dark',
      setMode: vi.fn(),
      resolvedMode: 'dark',
      setIsSettingsOpen: vi.fn(),
    })

    render(<ThemeToggle />)

    const activeLabels = screen.getAllByText('Active')
    expect(activeLabels.length).toBeGreaterThanOrEqual(1)
  })
})
