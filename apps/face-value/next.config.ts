import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  experimental: {
    // Your experimental flags here
  },
  outputFileTracingIncludes: {
    "next.config.js": ["**/*.ts", "**/*.tsx"],
  },
  typescript: {
    // See https://nextjs.org/docs/app/building-your-application/configuring/typescript
    // For more advanced types, visit https://nextjs.org/docs/app/building-your-application/typescript
  },
  webpack: (config, { isServer }) => {
    config.resolve.alias['@inference/ui'] = require.resolve('./packages/ui');
    return config;
  },
}

const nextConfig: NextConfig = {
  experimental: {
    // Your experimental flags here
  },
  outputFileTracingIncludes: {
    "next.config.js": ["**/*.ts", "**/*.tsx"],
  },
}

export default nextConfig