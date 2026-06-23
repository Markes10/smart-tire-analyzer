"use client"

import { useTheme } from "@/components/theme-provider"
import { themeTemplates, type ThemeMode } from "@/components/theme-templates"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Sun, Moon, Monitor, Check, Palette, Sliders, LayoutTemplate } from "lucide-react"
import { cn } from "@/lib/utils"

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

const modeOptions: { value: ThemeMode; label: string; icon: React.ReactNode }[] = [
  { value: "light", label: "Light", icon: <Sun className="h-4 w-4" /> },
  { value: "dark", label: "Dark", icon: <Moon className="h-4 w-4" /> },
  { value: "system", label: "System", icon: <Monitor className="h-4 w-4" /> },
]

export function ThemeSettings() {
  const {
    mode,
    setMode,
    colors,
    setColors,
    activeTemplate,
    applyTemplate,
    isSettingsOpen,
    setIsSettingsOpen,
  } = useTheme()

  return (
    <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5 text-primary" />
            Theme Settings
          </DialogTitle>
          <DialogDescription>
            Customize the appearance of the app. Changes are applied instantly and saved automatically.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="templates" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="templates" className="flex items-center gap-2">
              <LayoutTemplate className="h-4 w-4" />
              <span className="hidden sm:inline">Templates</span>
            </TabsTrigger>
            <TabsTrigger value="colors" className="flex items-center gap-2">
              <Palette className="h-4 w-4" />
              <span className="hidden sm:inline">Colors</span>
            </TabsTrigger>
            <TabsTrigger value="advanced" className="flex items-center gap-2">
              <Sliders className="h-4 w-4" />
              <span className="hidden sm:inline">Advanced</span>
            </TabsTrigger>
          </TabsList>

          {/* Templates Tab */}
          <TabsContent value="templates" className="mt-4 space-y-4">
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">Design Templates</h3>
              <div className="grid grid-cols-2 gap-3">
                {themeTemplates.map((template) => (
                  <Card
                    key={template.id}
                    className={cn(
                      "cursor-pointer transition-all hover:border-primary/50",
                      activeTemplate === template.id && "border-primary ring-1 ring-primary"
                    )}
                    onClick={() => applyTemplate(template.id)}
                  >
                    <CardHeader className="p-3 pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">{template.name}</CardTitle>
                        {activeTemplate === template.id && (
                          <Check className="h-4 w-4 text-primary" />
                        )}
                      </div>
                      <CardDescription className="text-xs">{template.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="p-3 pt-0">
                      <div
                        className="h-10 rounded-md border border-border/50 flex items-center justify-center gap-2 px-3"
                        style={{ backgroundColor: template.preview.background }}
                      >
                        <div
                          className="h-4 w-4 rounded-full"
                          style={{ backgroundColor: template.preview.primary }}
                        />
                        <span className="text-xs font-medium" style={{ color: template.preview.foreground }}>
                          Preview
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Colors Tab */}
          <TabsContent value="colors" className="mt-4 space-y-6">
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">Mode</h3>
              <div className="flex gap-2">
                {modeOptions.map((option) => (
                  <Button
                    key={option.value}
                    variant={mode === option.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setMode(option.value)}
                    className="flex items-center gap-2"
                  >
                    {option.icon}
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">Primary Color</h3>
              <div className="grid grid-cols-4 gap-2">
                {colorPresets.map((preset) => (
                  <button type="button"
                    key={preset.hue}
                    onClick={() => setColors({ ...colors, primary: preset.hue })}
                    className={cn(
                      "flex flex-col items-center gap-1.5 p-2 rounded-lg border transition-all hover:border-primary/50",
                      colors.primary === preset.hue && "border-primary ring-1 ring-primary bg-primary/5"
                    )}
                    aria-label={`Set primary color to ${preset.name}`}
                  >
                    <div
                      className="h-8 w-8 rounded-full border border-border/50"
                      style={{ backgroundColor: preset.color }}
                    />
                    <span className="text-xs text-muted-foreground">{preset.name}</span>
                    {colors.primary === preset.hue && (
                      <Check className="h-3 w-3 text-primary" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Advanced Tab */}
          <TabsContent value="advanced" className="mt-4 space-y-6">
            <div>
              <Label className="text-sm font-medium text-foreground mb-3 block">
                Primary Hue: {colors.primary}°
              </Label>
              <Slider
                value={[parseInt(colors.primary)]}
                min={0}
                max={360}
                step={1}
                onValueChange={([value]) => setColors({ ...colors, primary: value.toString() })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>0° Red</span>
                <span>120° Green</span>
                <span>240° Blue</span>
                <span>360° Red</span>
              </div>
            </div>

            <div>
              <Label className="text-sm font-medium text-foreground mb-3 block">
                Secondary Hue: {colors.secondary}°
              </Label>
              <Slider
                value={[parseInt(colors.secondary)]}
                min={0}
                max={360}
                step={1}
                onValueChange={([value]) => setColors({ ...colors, secondary: value.toString() })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>0° Red</span>
                <span>120° Green</span>
                <span>240° Blue</span>
                <span>360° Red</span>
              </div>
            </div>

            <div className="rounded-lg border border-border/50 p-4 bg-card/50">
              <h4 className="text-sm font-medium text-foreground mb-2">Current Values</h4>
              <div className="space-y-1 font-mono text-xs text-muted-foreground">
                <div>Primary: oklch(0.65 0.2 {colors.primary})</div>
                <div>Background: oklch(0.1 0.005 {colors.secondary})</div>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end mt-4">
          <Button variant="outline" onClick={() => setIsSettingsOpen(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
