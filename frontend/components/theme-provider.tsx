"use client"

import * as React from "react"
import { createContext, useContext, useEffect, useState, useCallback } from "react"

export type ThemeMode = "light" | "dark" | "system"

export interface ThemeColors {
  primary: string
  secondary: string
}

export interface ThemeTemplate {
  id: string
  name: string
  description: string
  mode: ThemeMode
  colors: ThemeColors
  preview: {
    background: string
    foreground: string
    primary: string
  }
}

export const themeTemplates: ThemeTemplate[] = [
  {
    id: "default-dark",
    name: "Automotive Dark",
    description: "Default dark theme with teal accents",
    mode: "dark",
    colors: { primary: "160", secondary: "260" },
    preview: { background: "#0d0d11", foreground: "#f2f2f2", primary: "#10b981" },
  },
  {
    id: "ocean-dark",
    name: "Ocean Night",
    description: "Deep blue theme for focused work",
    mode: "dark",
    colors: { primary: "220", secondary: "240" },
    preview: { background: "#0a1628", foreground: "#e2e8f0", primary: "#3b82f6" },
  },
  {
    id: "sunset-dark",
    name: "Sunset Drive",
    description: "Warm amber tones for comfort",
    mode: "dark",
    colors: { primary: "35", secondary: "15" },
    preview: { background: "#1c1412", foreground: "#fef3c7", primary: "#f59e0b" },
  },
  {
    id: "rose-dark",
    name: "Rose Garage",
    description: "Modern rose accent theme",
    mode: "dark",
    colors: { primary: "350", secondary: "280" },
    preview: { background: "#18101a", foreground: "#fce7f3", primary: "#ec4899" },
  },
  {
    id: "default-light",
    name: "Clean Light",
    description: "Bright theme for daytime use",
    mode: "light",
    colors: { primary: "160", secondary: "220" },
    preview: { background: "#ffffff", foreground: "#1f2937", primary: "#10b981" },
  },
  {
    id: "ocean-light",
    name: "Sky Blue",
    description: "Calm blue light theme",
    mode: "light",
    colors: { primary: "220", secondary: "200" },
    preview: { background: "#f8fafc", foreground: "#1e293b", primary: "#3b82f6" },
  },
]

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

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "dark"
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("dark")
  const [colors, setColorsState] = useState<ThemeColors>({ primary: "160", secondary: "260" })
  const [activeTemplate, setActiveTemplate] = useState<string | null>("default-dark")
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  const resolvedMode = mode === "system" ? getSystemTheme() : mode

  useEffect(() => {
    setMounted(true)
    const savedTheme = localStorage.getItem("smart-tire-theme")
    if (savedTheme) {
      try {
        const parsed = JSON.parse(savedTheme)
        setModeState(parsed.mode || "dark")
        setColorsState(parsed.colors || { primary: "160", secondary: "260" })
        setActiveTemplate(parsed.activeTemplate || null)
      } catch {
        // Use defaults
      }
    }
  }, [])

  useEffect(() => {
    if (!mounted) return
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
  }, [mode, colors, resolvedMode, mounted])

  const saveTheme = useCallback((newMode: ThemeMode, newColors: ThemeColors, newTemplate: string | null) => {
    localStorage.setItem("smart-tire-theme", JSON.stringify({
      mode: newMode,
      colors: newColors,
      activeTemplate: newTemplate,
    }))
  }, [])

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode)
    setActiveTemplate(null)
    saveTheme(newMode, colors, null)
  }, [colors, saveTheme])

  const setColors = useCallback((newColors: ThemeColors) => {
    setColorsState(newColors)
    setActiveTemplate(null)
    saveTheme(mode, newColors, null)
  }, [mode, saveTheme])

  const applyTemplate = useCallback((templateId: string) => {
    const template = themeTemplates.find(t => t.id === templateId)
    if (template) {
      setModeState(template.mode)
      setColorsState(template.colors)
      setActiveTemplate(templateId)
      saveTheme(template.mode, template.colors, templateId)
    }
  }, [saveTheme])

  useEffect(() => {
    if (mode !== "system") return
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => { setModeState("system") }
    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [mode])

  return (
    <ThemeContext.Provider value={{ mode, setMode, colors, setColors, activeTemplate, applyTemplate, resolvedMode, isSettingsOpen, setIsSettingsOpen }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider")
  }
  return context
}
