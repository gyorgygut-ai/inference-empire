import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  experimental: {
    agentUpgrade: "security",
  },
  outputFileTracingIncludes: {
    "/*": ["./outcomes/**/*"],
  },
  transpilePackages: ["@inference/ui"],
}

export default nextConfig
