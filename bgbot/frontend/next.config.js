const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const nextConfig = {reactStrictMode: true, async rewrites() {return [{source: "/api/:path*", destination: `${API_URL}/api/:path*`}, {source: "/auth/:path*", destination: `${API_URL}/auth/:path*`}];}};
module.exports = nextConfig;
