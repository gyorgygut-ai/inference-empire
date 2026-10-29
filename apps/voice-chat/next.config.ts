import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  experimental: {
  },
  transpilePackages: ["@inference/ui"],
}

export default nextConfig
