"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeSettings } from "@/components/theme-settings";
import RequireAuth from "@/components/RequireAuth";

export default function AuthWrapper({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider>
        <RequireAuth>{children}</RequireAuth>
        <ThemeSettings />
      </ThemeProvider>
    </SessionProvider>
  );
}
