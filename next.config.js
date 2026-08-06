// BUILD_TARGET=native => export statique bundlé dans l'app iOS/Android (Capacitor).
// Sinon => build web classique (proxy /api, headers). Le web n'est JAMAIS impacté.
const NATIVE = process.env.BUILD_TARGET === 'native'

const nextConfig = {
  ...(NATIVE ? { output: 'export', trailingSlash: true } : {}),
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: 'https', hostname: 'avatars.githubusercontent.com', pathname: '/**' },
    ],
  },
  // Proxy same-origin : toutes les requêtes /api/* du front sont relayées vers le
  // backend Python (FastAPI). Définir BACKEND_URL (ex: https://divarc-api.up.railway.app).
  // Avantage : pas de CORS, et les <img src="/api/market/image/..."> fonctionnent tel quel.
  async rewrites() {
    if (NATIVE) return []
    const api = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '')
    return api ? [{ source: '/api/:path*', destination: `${api}/api/:path*` }] : []
  },
  webpack(config, { dev }) {
    if (dev) {
      // Reduce CPU/memory from file watching
      config.watchOptions = {
        poll: 2000, // check every 2 seconds
        aggregateTimeout: 300, // wait before rebuilding
        ignored: ['**/node_modules'],
      };
    }
    return config;
  },
  onDemandEntries: {
    maxInactiveAge: 10000,
    pagesBufferLength: 2,
  },
  async headers() {
    if (NATIVE) return []
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "ALLOWALL" },
          { key: "Content-Security-Policy", value: "frame-ancestors *;" },
          { key: "Access-Control-Allow-Origin", value: process.env.CORS_ORIGINS || "*" },
          { key: "Access-Control-Allow-Methods", value: "GET, POST, PUT, DELETE, OPTIONS" },
          { key: "Access-Control-Allow-Headers", value: "*" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
