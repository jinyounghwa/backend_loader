"use client"

import { signIn } from "next-auth/react"
import { useSearchParams } from "next/navigation"

export function LoginForm() {
  const searchParams = useSearchParams()
  const callbackUrl = searchParams.get("callbackUrl") || "/"

  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-center text-2xl font-bold text-slate-900">
          AWS Guardian
        </h1>
        <p className="mb-8 text-center text-sm text-slate-600">
          Sign in with GitHub to continue
        </p>

        <button
          onClick={() => signIn("github", { callbackUrl })}
          className="w-full rounded-lg bg-slate-900 py-2 px-4 font-semibold text-white hover:bg-slate-800 transition-colors"
        >
          Sign in with GitHub
        </button>
      </div>
    </div>
  )
}
