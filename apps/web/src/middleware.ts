import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export async function middleware(request: NextRequest) {
  if (process.env.AWS_ENV === "localstack") {
    return NextResponse.next()
  }

  const { auth } = await import("@auth")
  return (auth as Function)(request)
}

export const config = {
  matcher: ["/((?!api/auth|login|_next/static|favicon.ico).*)"],
}
