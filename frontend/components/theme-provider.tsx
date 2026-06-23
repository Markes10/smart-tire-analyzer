"use client"

import * as React from "react"
import { createContext, use, useCallback, useEffect, useMemo, useState } from "react"
import { themeTemplates, type ThemeColors, type ThemeMode } from "@/components/theme-templates"

interface ThemeContextType {
  mode: ThemeMode
  setMode: (mode: ThemeMode) => void
  colors: ThemeColors
  setColors: (colors: ThemeColors) => void
  activeTemplate: string | null
  applyTemplate: (templateId: string) => void
  resolvedMode: "light" | "dark"
  isSettingsOpen: boolean
  setIsSettingsOpen: (open: boolean) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)
const THEME_STORAGE_KEY = "smart-tire:v1:theme"
const defaultTheme = {
  mode: "dark" as ThemeMode,
  colors: { primary: "160", secondary: "260" },
  activeTemplate: "default-dark" as string | null,
}

function getStoredTheme() {
  if (typeof window === "undefined") return defaultTheme

  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) ?? localStorage.getItem("smart-tire-theme")
  if (!savedTheme) return defaultTheme

  try {
    const parsed = JSON.parse(savedTheme)
    return {
      mode: parsed.mode || defaultTheme.mode,
      colors: parsed.colors || defaultTheme.colors,
      activeTemplate: parsed.activeTemplate || null,
    }
  } catch {
    return defaultTheme
  }
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "dark"
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState(getStoredTheme)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const { mode, colors, activeTemplate } = theme

  const resolvedMode = mode === "system" ? getSystemTheme() : mode

  useEffect(() => {
    const root = document.documentElement
    if (resolvedMode === "dark") {
      root.classList.add("dark")
      root.classList.remove("light")
    } else {
      root.classList.add("light")
      root.classList.remove("dark")
    }
    const primaryHue = colors.primary
    const secondaryHue = colors.secondary
    if (resolvedMode === "dark") {
      root.style.setProperty("--primary", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--primary-foreground", `oklch(0.1 0.005 ${secondaryHue})`)
      root.style.setProperty("--accent", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--accent-foreground", `oklch(0.1 0.005 ${secondaryHue})`)
      root.style.setProperty("--ring", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--chart-1", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--sidebar-primary", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--sidebar-ring", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--success", `oklch(0.65 0.2 ${primaryHue})`)
      root.style.setProperty("--background", `oklch(0.1 0.005 ${secondaryHue})`)
      root.style.setProperty("--foreground", "oklch(0.95 0 0)")
      root.style.setProperty("--card", `oklch(0.14 0.005 ${secondaryHue})`)
      root.style.setProperty("--card-foreground", "oklch(0.95 0 0)")
      root.style.setProperty("--popover", `oklch(0.14 0.005 ${secondaryHue})`)
      root.style.setProperty("--popover-foreground", "oklch(0.95 0 0)")
      root.style.setProperty("--secondary", `oklch(0.2 0.01 ${secondaryHue})`)
      root.style.setProperty("--secondary-foreground", "oklch(0.95 0 0)")
      root.style.setProperty("--muted", `oklch(0.18 0.005 ${secondaryHue})`)
      root.style.setProperty("--muted-foreground", "oklch(0.6 0 0)")
      root.style.setProperty("--border", `oklch(0.25 0.01 ${secondaryHue})`)
      root.style.setProperty("--input", `oklch(0.2 0.005 ${secondaryHue})`)
      root.style.setProperty("--sidebar", `oklch(0.12 0.005 ${secondaryHue})`)
      root.style.setProperty("--sidebar-foreground", "oklch(0.95 0 0)")
      root.style.setProperty("--sidebar-accent", `oklch(0.2 0.01 ${secondaryHue})`)
      root.style.setProperty("--sidebar-accent-foreground", "oklch(0.95 0 0)")
      root.style.setProperty("--sidebar-border", `oklch(0.25 0.01 ${secondaryHue})`)
    } else {
      root.style.setProperty("--primary", `oklch(0.5 0.2 ${primaryHue})`)
      root.style.setProperty("--primary-foreground", "oklch(0.98 0 0)")
      root.style.setProperty("--accent", `oklch(0.95 0.03 ${primaryHue})`)
      root.style.setProperty("--accent-foreground", `oklch(0.3 0.1 ${primaryHue})`)
      root.style.setProperty("--ring", `oklch(0.5 0.2 ${primaryHue})`)
      root.style.setProperty("--chart-1", `oklch(0.5 0.2 ${primaryHue})`)
      root.style.setProperty("--sidebar-primary", `oklch(0.5 0.2 ${primaryHue})`)
      root.style.setProperty("--sidebar-ring", `oklch(0.5 0.2 ${primaryHue})`)
      root.style.setProperty("--success", `oklch(0.5 0.2 ${primaryHue})`)
      root.style.setProperty("--background", "oklch(0.99 0.002 0)")
      root.style.setProperty("--foreground", `oklch(0.15 0.01 ${secondaryHue})`)
      root.style.setProperty("--card", "oklch(1 0 0)")
      root.style.setProperty("--card-foreground", `oklch(0.15 0.01 ${secondaryHue})`)
      root.style.setProperty("--popover", "oklch(1 0 0)")
      root.style.setProperty("--popover-foreground", `oklch(0.15 0.01 ${secondaryHue})`)
      root.style.setProperty("--secondary", `oklch(0.96 0.005 ${secondaryHue})`)
      root.style.setProperty("--secondary-foreground", `oklch(0.2 0.01 ${secondaryHue})`)
      root.style.setProperty("--muted", `oklch(0.96 0.005 ${secondaryHue})`)
      root.style.setProperty("--muted-foreground", `oklch(0.45 0.01 ${secondaryHue})`)
      root.style.setProperty("--border", `oklch(0.92 0.005 ${secondaryHue})`)
      root.style.setProperty("--input", `oklch(0.92 0.005 ${secondaryHue})`)
      root.style.setProperty("--sidebar", `oklch(0.98 0.002 ${secondaryHue})`)
      root.style.setProperty("--sidebar-foreground", `oklch(0.15 0.01 ${secondaryHue})`)
      root.style.setProperty("--sidebar-accent", `oklch(0.96 0.005 ${secondaryHue})`)
      root.style.setProperty("--sidebar-accent-foreground", `oklch(0.2 0.01 ${secondaryHue})`)
      root.style.setProperty("--sidebar-border", `oklch(0.92 0.005 ${secondaryHue})`)
    }
  }, [mode, colors, resolvedMode])

  const saveTheme = useCallback((newMode: ThemeMode, newColors: ThemeColors, newTemplate: string | null) => {
    localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify({
      mode: newMode,
      colors: newColors,
      activeTemplate: newTemplate,
    }))
  }, [])

  const setMode = useCallback((newMode: ThemeMode) => {
    setTheme((current) => {
      const next = { ...current, mode: newMode, activeTemplate: null }
      saveTheme(next.mode, next.colors, next.activeTemplate)
      return next
    })
  }, [saveTheme])

  const setColors = useCallback((newColors: ThemeColors) => {
    setTheme((current) => {
      const next = { ...current, colors: newColors, activeTemplate: null }
      saveTheme(next.mode, next.colors, next.activeTemplate)
      return next
    })
  }, [saveTheme])

  const applyTemplate = useCallback((templateId: string) => {
    const template = themeTemplates.find(t => t.id === templateId)
    if (template) {
      setTheme({ mode: template.mode, colors: template.colors, activeTemplate: templateId })
      saveTheme(template.mode, template.colors, templateId)
    }
  }, [saveTheme])

  useEffect(() => {
    if (mode !== "system") return
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => setTheme((current) => ({ ...current }))
    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [mode])

  const value = useMemo(
    () => ({ mode, setMode, colors, setColors, activeTemplate, applyTemplate, resolvedMode, isSettingsOpen, setIsSettingsOpen }),
    [mode, setMode, colors, setColors, activeTemplate, applyTemplate, resolvedMode, isSettingsOpen],
  )

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = use(ThemeContext)
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider")
  }
  return context
}
