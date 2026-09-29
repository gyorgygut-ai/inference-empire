import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  experimental: {
  },
  outputFileTracingIncludes: {
    "/*": ["./outcomes/**/*"],
  },
}

export default nextConfig