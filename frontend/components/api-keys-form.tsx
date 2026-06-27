"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Switch } from "@/components/ui/switch"
import { Key, ExternalLink, AlertCircle, CheckCircle2, Shield } from "lucide-react"
import type { UserApiKeyPreferences } from "@/lib/api-keys"

interface ApiKeysFormProps {
  initialPrefs?: Partial<UserApiKeyPreferences>
  onSave: (prefs: Partial<UserApiKeyPreferences>) => void
  saving?: boolean
}

/**
 * API Key form — now only stores boolean preferences in the browser.
 * Actual API keys are submitted via the sign-up flow and stored encrypted
 * server-side, or passed one-time through the backend during analysis.
 */
export function ApiKeysForm({ initialPrefs = {}, onSave, saving }: ApiKeysFormProps) {
  const [prefs, setPrefs] = useState<Partial<UserApiKeyPreferences>>(initialPrefs)

  const togglePref = (field: keyof UserApiKeyPreferences) => {
    setPrefs((prev) => ({ ...prev, [field]: !prev[field] }))
  }

  const enabledCount = Object.values(prefs).filter(Boolean).length

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5 text-primary" />
          API Key Services
        </CardTitle>
        <CardDescription>
          Choose which services use your own API keys (configured during sign-up
          and stored encrypted server-side). Toggle each service on or off.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {enabledCount > 0 && (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              {enabledCount} of 3 services configured to use your own keys
            </AlertDescription>
          </Alert>
        )}

        <Alert className="border-primary/30 bg-primary/5">
          <Shield className="h-4 w-4 text-primary" />
          <AlertDescription className="text-xs">
            Security: Your API keys are never stored in your browser. They are
            submitted securely during sign-up and encrypted at rest (AES-256-GCM)
            on the server. You control which services use your keys via toggles below.
          </AlertDescription>
        </Alert>

        {/* Gemini API Key */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="useOwnGemini" className="font-medium">
                Use My Gemini Key
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                AI tire reasoning and sidewall text extraction
              </p>
            </div>
            <Switch
              id="useOwnGemini"
              checked={prefs.useOwnGemini ?? false}
              onCheckedChange={() => togglePref("useOwnGemini")}
            />
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get a Gemini API key <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <Separator />

        {/* Mapillary Access Token */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="useOwnMapillary" className="font-medium">
                Use My Mapillary Token
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Street-level road imagery for surface texture analysis
              </p>
            </div>
            <Switch
              id="useOwnMapillary"
              checked={prefs.useOwnMapillary ?? false}
              onCheckedChange={() => togglePref("useOwnMapillary")}
            />
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://www.mapillary.com/dashboard/developers"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get a Mapillary token <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <Separator />

        {/* OpenWeather API Key */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="useOwnOpenweather" className="font-medium">
                Use My OpenWeather Key
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Weather-based tire risk assessment
              </p>
            </div>
            <Switch
              id="useOwnOpenweather"
              checked={prefs.useOwnOpenweather ?? false}
              onCheckedChange={() => togglePref("useOwnOpenweather")}
            />
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://home.openweathermap.org/users/sign_up"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get an OpenWeather key <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        {!prefs.useOwnGemini && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              At minimum, a Gemini key should be enabled for AI tire analysis.
              You can set your keys during sign-up in your account settings.
            </AlertDescription>
          </Alert>
        )}

        <Button onClick={() => onSave(prefs)} disabled={saving} className="w-full">
          {saving ? "Saving…" : "Save Preferences"}
        </Button>
      </CardContent>
    </Card>
  )
}
