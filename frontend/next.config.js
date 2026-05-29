/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001',
  },
  // livekit-server-sdk needs to be transpiled (uses ES module exports)
  transpilePackages: ['livekit-server-sdk'],
}

module.exports = nextConfig
