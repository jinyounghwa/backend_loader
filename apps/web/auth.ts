import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"

const ADMIN_EMAILS = (process.env.ADMIN_EMAILS ?? "").split(",").filter(Boolean)

const providers = []

if (process.env.AUTH_GITHUB_ID && process.env.AUTH_GITHUB_SECRET) {
  providers.push(GitHub)
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  callbacks: {
    jwt({ token, user }) {
      if (user?.email) {
        token.role = ADMIN_EMAILS.includes(user.email) ? "admin" : "viewer"
      }
      return token
    },
    session({ session, token }) {
      if (session.user && token.role) {
        session.user.role = token.role as "admin" | "viewer"
      }
      return session
    },
  },
})
