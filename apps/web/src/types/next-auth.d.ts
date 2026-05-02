import { DefaultSession } from "next-auth"

declare module "next-auth" {
  interface User {
    role?: "admin" | "viewer"
  }

  interface Session {
    user: {
      role?: "admin" | "viewer"
    } & DefaultSession["user"]
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    role?: "admin" | "viewer"
  }
}
