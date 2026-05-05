import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"
import Credentials from "next-auth/providers/credentials"

const ADMIN_EMAILS = (process.env.ADMIN_EMAILS ?? "").split(",").filter(Boolean)
const isLocalDev = process.env.AWS_ENV === "localstack"

const providers = []

if (process.env.AUTH_GITHUB_ID && process.env.AUTH_GITHUB_SECRET) {
  providers.push(GitHub)
}

if (isLocalDev) {
  providers.push(
    Credentials({
      name: "Local Dev",
      credentials: { email: { label: "Email", type: "email" } },
      async authorize() {
        return { id: "local-dev", email: "admin@localhost", name: "Local Admin" }
      },
    })
  )
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  callbacks: {
    jwt({ token, user }) {
      if (user?.email) {
        token.role = ADMIN_EMAILS.includes(user.email) ? "admin" : "viewer"
      }
      if (isLocalDev && !token.role) {
        token.role = "admin"
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
