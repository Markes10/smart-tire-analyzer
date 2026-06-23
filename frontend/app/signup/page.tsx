"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Gauge, ArrowLeft, AlertCircle, CheckCircle2 } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ApiKeysForm } from "@/components/api-keys-form"
import { saveApiKeys } from "@/lib/api-keys"
import type { UserApiKeys } from "@/lib/api-keys"

export default function SignUpPage() {
  const { push } = useRouter()
  const [step, setStep] = useState<"account" | "keys">("account")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [savingKeys, setSavingKeys] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleAccountSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    if (password.length < 4) {
      setError("Password must be at least 4 characters.")
      setIsLoading(false)
      return
    }

    // Create session with credentials
    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      })

      if (result?.error) {
        setError("Could not create account. Please try again.")
        setIsLoading(false)
        return
      }

      if (result?.ok) {
        // Move to API keys step
        setStep("keys")
        setIsLoading(false)
      }
    } catch {
      setError("An unexpected error occurred.")
      setIsLoading(false)
    }
  }

  const handleKeysSave = async (keys: Partial<UserApiKeys>) => {
    setSavingKeys(true)
    setError(null)

    try {
      saveApiKeys(keys)
      setSuccess(true)
      setTimeout(() => push("/analyze"), 1500)
    } catch {
      setError("Failed to save API keys. Please try again.")
      setSavingKeys(false)
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
              <CheckCircle2 className="h-8 w-8 text-success" />
            </div>
            <CardTitle className="text-2xl">Welcome aboard!</CardTitle>
            <CardDescription>
              Your account is set up. Redirecting you to the analyzer…
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="h-125 w-125 rounded-full bg-primary/10 blur-[100px]" />
        </div>
      </div>

      <Button variant="ghost" className="absolute left-4 top-4 gap-1" asChild>
        <Link href="/">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
      </Button>

      {step === "account" && (
        <Card className="w-full max-w-md border-border/50 bg-card/80 backdrop-blur-xl">
          <CardHeader className="space-y-1 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
              <Gauge className="h-6 w-6 text-primary-foreground" />
            </div>
            <CardTitle className="text-2xl">Create your account</CardTitle>
            <CardDescription>
              Sign up to start analyzing tire health with AI
            </CardDescription>
          </CardHeader>

          {error && (
            <div className="px-6 pb-2">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </div>
          )}

          <form onSubmit={handleAccountSubmit}>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    placeholder="John"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    placeholder="Doe"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="At least 4 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={4}
                  disabled={isLoading}
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Creating account…" : "Create Account"}
              </Button>

              <div className="relative w-full">
                <Separator />
                <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
                  next step
                </span>
              </div>

              <p className="text-center text-sm text-muted-foreground">
                {"Already have an account? "}
                <Link href="/login" className="font-medium text-foreground hover:underline">
                  Sign in
                </Link>
              </p>

              <p className="text-center text-xs text-muted-foreground/60">
                After creating your account, you&apos;ll configure your API keys
              </p>
            </CardFooter>
          </form>
        </Card>
      )}

      {step === "keys" && (
        <div className="w-full max-w-lg">
          <div className="mb-6 text-center">
            <h2 className="text-xl font-semibold text-foreground">Configure Your API Keys</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Enter your own API keys to unlock all features. You can skip or change these later in Settings.
            </p>
          </div>

          {error && (
            <div className="mb-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </div>
          )}

          <ApiKeysForm onSave={handleKeysSave} saving={savingKeys} />

          <div className="mt-4 text-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                saveApiKeys({})
                push("/analyze")
              }}
            >
              Skip for now &mdash; I&apos;ll add keys later
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
