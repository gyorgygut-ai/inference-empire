import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  experimental: {
  },
  outputFileTracingIncludes: {
    "/*": ["./outcomes/**/*"],
  },
  transpilePackages: ["@inference/ui"],
}

export default nextConfig