import { Suspense } from "react"
import LoginForm from "./LoginForm"

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg text-muted-foreground">Loading…</div>
      </div>
    }>
      <LoginForm />
    </Suspense>
  )
}
