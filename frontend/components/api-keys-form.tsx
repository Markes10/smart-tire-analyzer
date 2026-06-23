"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Key, Eye, EyeOff, ExternalLink, AlertCircle, CheckCircle2 } from "lucide-react"
import type { UserApiKeys } from "@/lib/api-keys"

interface ApiKeysFormProps {
  initialKeys?: Partial<UserApiKeys>
  onSave: (keys: Partial<UserApiKeys>) => void
  saving?: boolean
}

export function ApiKeysForm({ initialKeys = {}, onSave, saving }: ApiKeysFormProps) {
  const [keys, setKeys] = useState<Partial<UserApiKeys>>(initialKeys)
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})

  const toggleVisible = (field: string) => {
    setShowSecrets((prev) => ({ ...prev, [field]: !prev[field] }))
  }

  const updateKey = (field: keyof UserApiKeys, value: string) => {
    setKeys((prev) => ({ ...prev, [field]: value }))
  }

  const configuredCount = Object.values(keys).filter(Boolean).length

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5 text-primary" />
          API Keys — Bring Your Own
        </CardTitle>
        <CardDescription>
          Enter your own API keys to enable AI analysis, maps, and weather features.
          Keys are stored in your browser and sent with each analysis request.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {configuredCount > 0 && (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              {configuredCount} of 4 API keys configured
            </AlertDescription>
          </Alert>
        )}

        {/* Gemini API Key */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="gemini" className="font-medium">
              Gemini API Key <span className="text-xs text-muted-foreground">(required for AI analysis)</span>
            </Label>
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get key <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="relative">
            <Input
              id="gemini"
              type={showSecrets.gemini ? "text" : "password"}
              placeholder="AIzaSy..."
              value={keys.gemini || ""}
              onChange={(e) => updateKey("gemini", e.target.value)}
            />
            <button
              type="button"
              onClick={() => toggleVisible("gemini")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showSecrets.gemini ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Get a free API key from Google AI Studio. Used for AI tire reasoning and sidewall text extraction.
          </p>
        </div>

        <Separator />

        {/* Mapillary Access Token — replaces Google Maps */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="mapillary" className="font-medium">
              Mapillary Access Token <span className="text-xs text-muted-foreground">(replaces Google Maps — road imagery)</span>
            </Label>
            <a
              href="https://www.mapillary.com/dashboard/developers"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get token <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="relative">
            <Input
              id="mapillary"
              type={showSecrets.mapillary ? "text" : "password"}
              placeholder="MLY|..."
              value={keys.mapillary || ""}
              onChange={(e) => updateKey("mapillary", e.target.value)}
            />
            <button
              type="button"
              onClick={() => toggleVisible("mapillary")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showSecrets.mapillary ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Register an app at mapillary.com/dashboard/developers to get your Client Token.
            Used to fetch street-level road imagery for surface texture analysis — replaces Google Maps.
          </p>
        </div>

        <Separator />

        {/* OpenWeather API Key */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="openweather" className="font-medium">
              OpenWeather API Key <span className="text-xs text-muted-foreground">(optional — weather data)</span>
            </Label>
            <a
              href="https://home.openweathermap.org/users/sign_up"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get key <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="relative">
            <Input
              id="openweather"
              type={showSecrets.openweather ? "text" : "password"}
              placeholder="abc123..."
              value={keys.openweather || ""}
              onChange={(e) => updateKey("openweather", e.target.value)}
            />
            <button
              type="button"
              onClick={() => toggleVisible("openweather")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showSecrets.openweather ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Sign up at openweathermap.org for a free API key. Used for weather-based tire risk assessment.
          </p>
        </div>

        <Separator />

        {/* Google OAuth (optional — for login) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="googleClientId" className="font-medium">
              Google OAuth Client ID <span className="text-xs text-muted-foreground">(optional — Google login)</span>
            </Label>
            <a
              href="https://console.cloud.google.com/apis/credentials"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Get key <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <Input
            id="googleClientId"
            type="text"
            placeholder="123456-abc.apps.googleusercontent.com"
            value={keys.googleClientId || ""}
            onChange={(e) => updateKey("googleClientId", e.target.value)}
          />
          <div className="space-y-2">
            <Label htmlFor="googleClientSecret">Google OAuth Client Secret</Label>
            <div className="relative">
              <Input
                id="googleClientSecret"
                type={showSecrets.googleClientSecret ? "text" : "password"}
                placeholder="GOCSPX-..."
                value={keys.googleClientSecret || ""}
                onChange={(e) => updateKey("googleClientSecret", e.target.value)}
              />
              <button
                type="button"
                onClick={() => toggleVisible("googleClientSecret")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showSecrets.googleClientSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Create an OAuth 2.0 Web Application credential in Google Cloud Console. Add redirect URI:{" "}
            <code className="bg-muted px-1 rounded">http://localhost:8081/api/auth/callback/google</code>
          </p>
        </div>

        {!keys.gemini && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              At minimum, a Gemini API key is needed for AI tire analysis. You can add the others later.
            </AlertDescription>
          </Alert>
        )}

        <Button onClick={() => onSave(keys)} disabled={saving} className="w-full">
          {saving ? "Saving…" : configuredCount > 0 ? "Update API Keys" : "Save API Keys"}
        </Button>
      </CardContent>
    </Card>
  )
}
