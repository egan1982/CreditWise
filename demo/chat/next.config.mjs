/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/sop/:path*',
        destination: 'http://127.0.0.1:8200/sop/:path*',
      },
    ]
  },
}

export default nextConfig
