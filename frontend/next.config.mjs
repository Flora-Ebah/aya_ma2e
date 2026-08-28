/** @type {import('next').NextConfig} */

// Content-Security-Policy — restreint ce que le navigateur autorise à charger.
// 'unsafe-inline' est requis par Tailwind + Next hydration inline scripts.
// Si on veut plus strict à terme : passer aux CSP nonces (nécessite refactor).
const IS_DEV = process.env.NODE_ENV !== "production";

const CSP_DIRECTIVES = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  // Prod : HTTPS uniquement ; dev : autorise http:// pour appeler le backend local.
  IS_DEV ? "connect-src 'self' http: https: ws: wss:" : "connect-src 'self' https: wss:",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  // Prod uniquement : force les requêtes en HTTPS. En dev ça casserait localhost:8000.
  ...(IS_DEV ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const SECURITY_HEADERS = [
  // Force HTTPS pendant 1 an sur tous les sous-domaines.
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" },
  // Empêche le navigateur de « deviner » le type MIME (protection contre XSS via upload).
  { key: "X-Content-Type-Options", value: "nosniff" },
  // Interdit l'inclusion du site dans un <iframe> (protection clickjacking).
  { key: "X-Frame-Options", value: "DENY" },
  // Réduit les infos envoyées dans le Referer aux domaines externes.
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // Désactive les APIs sensibles du navigateur qu'on n'utilise pas.
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  // CSP — dernière ligne de défense contre XSS.
  { key: "Content-Security-Policy", value: CSP_DIRECTIVES },
  // Protège contre les attaques cross-origin qui exploitent Spectre/Meltdown.
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  // Empêche les autres origines d'inclure nos ressources.
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
];

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,

  // Ne pas exposer « X-Powered-By: Next.js » — 1 info de moins pour un attaquant en reconnaissance.
  poweredByHeader: false,

  // Ne pas publier les .js.map en prod — donnerait le code source lisible.
  productionBrowserSourceMaps: false,

  // F-08 — retire les console.* en prod (empêche la fuite de paths internes,
  // stack traces et messages debug via la console du navigateur).
  compiler: IS_DEV ? {} : { removeConsole: { exclude: ["error", "warn"] } },

  async headers() {
    return [
      {
        // Applique les headers de sécurité à TOUTES les routes.
        source: "/:path*",
        headers: SECURITY_HEADERS,
      },
    ];
  },

  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
