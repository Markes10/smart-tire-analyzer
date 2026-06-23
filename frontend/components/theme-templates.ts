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
