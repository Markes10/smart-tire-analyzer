"use client"

import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { useTheme } from "@/components/theme-provider"
import { themeTemplates, type ThemeMode } from "@/components/theme-templates"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useState } from "react"
import { Sun, Moon, Monitor, Check, Palette, ArrowLeft, RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"
import { ApiKeysForm } from "@/components/api-keys-form"
import { getApiKeys, saveApiKeys } from "@/lib/api-keys"

const colorPresets = [
  { name: "Teal", hue: "160", color: "#10b981" },
  { name: "Blue", hue: "220", color: "#3b82f6" },
  { name: "Purple", hue: "280", color: "#8b5cf6" },
  { name: "Rose", hue: "350", color: "#ec4899" },
  { name: "Orange", hue: "35", color: "#f59e0b" },
  { name: "Red", hue: "15", color: "#ef4444" },
  { name: "Cyan", hue: "190", color: "#06b6d4" },
  { name: "Green", hue: "140", color: "#22c55e" },
]

const modeOptions: { value: ThemeMode; label: string; icon: React.ReactNode; description: string }[] = [
  { value: "light", label: "Light", icon: <Sun className="h-5 w-5" />, description: "Bright theme for daytime" },
  { value: "dark", label: "Dark", icon: <Moon className="h-5 w-5" />, description: "Easy on the eyes at night" },
  { value: "system", label: "System", icon: <Monitor className="h-5 w-5" />, description: "Match device settings" },
]

function settingsLivePreview() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Preview</CardTitle>
        <CardDescription>
          See how your selected theme looks across different UI elements
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Buttons</Label>
              <div className="flex flex-wrap gap-2">
                <Button size="sm">Primary</Button>
                <Button size="sm" variant="secondary">Secondary</Button>
                <Button size="sm" variant="outline">Outline</Button>
                <Button size="sm" variant="ghost">Ghost</Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Status Indicators</Label>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-success" />
                  <span className="text-sm text-muted-foreground">Success</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-warning" />
                  <span className="text-sm text-muted-foreground">Warning</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-critical" />
                  <span className="text-sm text-muted-foreground">Critical</span>
                </div>
              </div>
            </div>
          </div>
          <Card className="border-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Sample Analysis Card</CardTitle>
              <CardDescription>Tire health status preview</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-10 w-10 rounded-full bg-primary flex items-center justify-center">
                    <span className="text-sm font-bold text-primary-foreground">85</span>
                  </div>
                  <div>
                    <div className="text-sm font-medium">Good Condition</div>
                    <div className="text-xs text-muted-foreground">Last checked today</div>
                  </div>
                </div>
                <Button size="sm" variant="outline">Details</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>
  )
}

export default function SettingsPage() {
  const { 
    mode, 
    setMode, 
    colors, 
    setColors, 
    activeTemplate, 
    applyTemplate,
  } = useTheme()
  const [apiKeysRefresh, setApiKeysRefresh] = useState(0)

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      
      <main className="flex-1 pt-24 pb-16">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          {/* Page Header */}
          <div className="mb-8">
            <Link 
              href="/" 
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Settings</h1>
              <p className="mt-1 text-muted-foreground">
                Customize your experience and manage API keys
              </p>
            </div>
          </div>

          {/* API Keys Configuration */}
          <ApiKeysForm
            key={apiKeysRefresh}
            initialKeys={getApiKeys()}
            onSave={(keys) => {
              saveApiKeys(keys)
              setApiKeysRefresh((n) => n + 1)
            }}
          />

          <div className="mt-8 grid gap-8">
            {/* Appearance Mode */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sun className="h-5 w-5 text-primary" />
                  Appearance Mode
                </CardTitle>
                <CardDescription>
                  Choose how Smart Tire Analyzer looks on your device
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-3">
                  {modeOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setMode(option.value)}
                      className={cn(
                        "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                        mode === option.value
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      )}
                    >
                      <div className={cn(
                        "p-3 rounded-full",
                        mode === option.value ? "bg-primary text-primary-foreground" : "bg-muted"
                      )}>
                        {option.icon}
                      </div>
                      <div className="text-center">
                        <div className="font-medium text-foreground">{option.label}</div>
                        <div className="text-xs text-muted-foreground">{option.description}</div>
                      </div>
                      {mode === option.value && (
                        <Check className="h-4 w-4 text-primary" />
                      )}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Design Templates */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5 text-primary" />
                  Design Templates
                </CardTitle>
                <CardDescription>
                  Quick-apply a complete theme with colors and mode
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {themeTemplates.map((template) => (
                    <button
                      key={template.id}
                      type="button"
                      onClick={() => applyTemplate(template.id)}
                      className={cn(
                        "text-left rounded-lg border-2 overflow-hidden transition-all",
                        activeTemplate === template.id
                          ? "border-primary ring-2 ring-primary/20"
                          : "border-border hover:border-primary/50"
                      )}
                    >
                      {/* Theme Preview */}
                      <div
                        className="h-20 p-3"
                        style={{ backgroundColor: template.preview.background }}
                      >
                        <div className="h-full flex flex-col justify-between">
                          <div className="flex items-center gap-2">
                            <div
                              className="h-3 w-3 rounded-full"
                              style={{ backgroundColor: template.preview.primary }}
                            />
                            <div
                              className="h-2 w-16 rounded"
                              style={{ 
                                backgroundColor: template.preview.foreground,
                                opacity: 0.3 
                              }}
                            />
                          </div>
                          <div className="flex gap-2">
                            <div
                              className="h-6 w-16 rounded"
                              style={{ backgroundColor: template.preview.primary }}
                            />
                            <div
                              className="h-6 w-12 rounded border"
                              style={{ 
                                borderColor: template.preview.foreground,
                                opacity: 0.2 
                              }}
                            />
                          </div>
                        </div>
                      </div>
                      <div className="p-3 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-sm text-foreground">{template.name}</div>
                          <div className="text-xs text-muted-foreground">{template.description}</div>
                        </div>
                        {activeTemplate === template.id && (
                          <Check className="h-4 w-4 text-primary shrink-0" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Custom Colors */}
            <Card>
              <CardHeader>
                <CardTitle>Custom Colors</CardTitle>
                <CardDescription>
                  Fine-tune your theme with custom color selection
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {/* Primary Color */}
                <div>
                  <Label className="text-sm font-medium mb-3 block">Primary Accent Color</Label>
                  <div className="grid grid-cols-4 sm:grid-cols-8 gap-3">
                    {colorPresets.map((preset) => (
                      <button
                        key={preset.hue}
                        type="button"
                        onClick={() => setColors({ ...colors, primary: preset.hue })}
                        className={cn(
                          "flex flex-col items-center gap-2 p-2 rounded-lg border transition-all",
                          colors.primary === preset.hue
                            ? "border-primary bg-primary/10"
                            : "border-border hover:border-primary/50"
                        )}
                      >
                        <div
                          className={cn(
                            "h-10 w-10 rounded-full transition-all",
                            colors.primary === preset.hue && "ring-2 ring-offset-2 ring-offset-background"
                          )}
                          style={{
                            backgroundColor: preset.color,
                            "--tw-ring-color": colors.primary === preset.hue ? preset.color : "transparent",
                          } as React.CSSProperties}
                        />
                        <span className="text-xs text-muted-foreground">{preset.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Custom Hue Slider */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-sm font-medium">Custom Primary Hue</Label>
                    <span className="text-sm text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded">
                      {colors.primary}°
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div
                      className="h-12 w-12 rounded-lg border-2 border-border shrink-0"
                      style={{
                        backgroundColor: `oklch(0.65 0.2 ${colors.primary})`,
                      }}
                    />
                    <div className="flex-1 space-y-2">
                      <Slider
                        value={[parseInt(colors.primary)]}
                        onValueChange={([value]) => setColors({ ...colors, primary: value.toString() })}
                        min={0}
                        max={360}
                        step={1}
                      />
                      <div className="h-4 rounded-full overflow-hidden">
                        <div
                          className="h-full w-full"
                          style={{
                            background: "linear-gradient(to right, oklch(0.65 0.2 0), oklch(0.65 0.2 60), oklch(0.65 0.2 120), oklch(0.65 0.2 180), oklch(0.65 0.2 240), oklch(0.65 0.2 300), oklch(0.65 0.2 360))",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Background Tint */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-sm font-medium">Background Tint</Label>
                    <span className="text-sm text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded">
                      {colors.secondary}°
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div
                      className="h-12 w-12 rounded-lg border-2 border-border shrink-0"
                      style={{
                        backgroundColor: `oklch(0.15 0.02 ${colors.secondary})`,
                      }}
                    />
                    <div className="flex-1">
                      <Slider
                        value={[parseInt(colors.secondary)]}
                        onValueChange={([value]) => setColors({ ...colors, secondary: value.toString() })}
                        min={0}
                        max={360}
                        step={1}
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {settingsLivePreview()}

            {/* Mobile Reset Button */}
            <div className="sm:hidden">
              <Button 
                variant="outline" 
                onClick={() => applyTemplate("default-dark")}
                className="w-full"
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Reset to Default Theme
              </Button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
