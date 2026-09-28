import { NextResponse, NextRequest } from "next/server"
import { createRemoteJWKSet, jwtVerify } from "jose"

const CF_ACCESS_AUD = process.env.CF_ACCESS_AUD
const CF_TEAM_DOMAIN = process.env.CF_TEAM_DOMAIN

export async function proxy(req: NextRequest) {
  if (!CF_ACCESS_AUD || !CF_TEAM_DOMAIN) {
    return NextResponse.next()
  }

  const token = req.cookies.get("CF_Authorization")?.value

  if (!token) {
    return NextResponse.redirect(new URL(`https://${CF_TEAM_DOMAIN}/cdn-cgi/access/login`))
  }

  try {
    const certs = createRemoteJWKSet(
      new URL(`https://${CF_TEAM_DOMAIN}/cdn-cgi/access/certs`)
    )

    await jwtVerify(token, certs, { audience: CF_ACCESS_AUD })

    return NextResponse.next()
  } catch {
    return NextResponse.redirect(new URL(`https://${CF_TEAM_DOMAIN}/cdn-cgi/access/login`))
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
