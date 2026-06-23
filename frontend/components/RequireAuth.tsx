"use client";

import { useSession } from "next-auth/react";
import { usePathname } from "next/navigation";

// Pages that don't require authentication
const PUBLIC_PATHS = [
  "/",
  "/login",
  "/signup",
  "/about",
  "/blog",
  "/contact",
  "/documentation",
  "/technical-support",
  "/terms",
  "/cookies",
  "/api-docs",
  "/analyze",
  "/feedback",
  "/dashboard",
  "/history",
  "/settings",
  "/fleet",
];

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const pathname = usePathname();

  // Allow access to public pages without auth
  const isPublicPath = pathname !== null && PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(path + "/"));

  if (isPublicPath) {
    return <>{children}</>;
  }

  // For protected pages, show loading while checking session
  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-screen">
        <span className="text-lg">Loading…</span>
      </div>
    );
  }

  // No valid session on a protected page — redirect to login
  if (!session) {
    // Use window.location to redirect to login page
    if (typeof window !== "undefined") {
      window.location.href = `/login?callbackUrl=${encodeURIComponent(pathname)}`;
    }
    return (
      <div className="flex items-center justify-center min-h-screen flex-col gap-4">
        <span className="text-lg">Please log in to access this page</span>
        <a href="/login" className="text-primary hover:underline">Go to Login</a>
      </div>
    );
  }

  return <>{children}</>;
}
