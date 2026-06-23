import NextAuth, { type NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

const hasGoogleCredentials = !!(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);

const providers: NextAuthOptions["providers"] = [
  // Local email/password auth — works without any external service.
  // In dev mode, any email with password >= 4 chars works.
  // The special password "google-oauth" returns a mock Google profile.
  CredentialsProvider({
    id: "credentials",
    name: "Email & Password",
    credentials: {
      email: { label: "Email", type: "email" },
      password: { label: "Password", type: "password" },
    },
    async authorize(credentials) {
      if (!credentials?.email || !credentials?.password) {
        return null;
      }
      // Mock Google OAuth in dev mode
      if (credentials.password === "google-oauth") {
        return {
          id: "google-dev-user",
          name: "Google User",
          email: credentials.email as string,
          image: "https://lh3.googleusercontent.com/a/default-user",
        };
      }
      // In development, accept any email with password >= 4 chars
      // In production, replace this with a database lookup
      if (credentials.password.length < 4) {
        return null;
      }
      return {
        id: credentials.email as string,
        name: (credentials.email as string).split("@")[0],
        email: credentials.email as string,
        image: null,
      };
    },
  }),
];

// Only add real GoogleProvider when credentials are configured
if (hasGoogleCredentials) {
  providers.unshift(
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  );
}

const handler = NextAuth({
  providers: providers,
  secret: process.env.NEXTAUTH_SECRET || "smart-tire-local-dev-secret-change-in-production",
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email ?? undefined;
        token.name = user.name ?? undefined;
        token.picture = user.image ?? undefined;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.user.email = token.email ?? null;
        session.user.name = token.name ?? null;
        session.user.image = token.picture ?? null;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});

export const GET = handler;
export const POST = handler;
