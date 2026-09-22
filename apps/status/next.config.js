/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig

if (process.env.NODE_ENV === 'development') {
  const { setupDevBindings } = require('@cloudflare/next-on-pages/next-dev')
  setupDevBindings({
    bindings: {
      STATUS_D1: {
        type: 'd1',
        databaseId: '00000000-0000-0000-0000-000000000000',
      },
    },
  })
}
