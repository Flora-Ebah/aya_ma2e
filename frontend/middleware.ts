/**
 * F-08 — Anonymise les headers qui divulguent la pile technique.
 *
 * Le rapport pentest v1.0 (F-08) a montré que Wappalyzer identifiait
 * précisément Next.js 14.2.35, Nginx 1.22.1, React et Tailwind.
 * Ce middleware Next.js écrase les headers de la réponse pour ne plus
 * transmettre :
 *   - `Server: ...` (remplacé par "MA2E")
 *   - `X-Powered-By: ...` (retiré, complémentaire de `poweredByHeader: false`
 *     dans next.config.mjs)
 *   - `X-Nextjs-*` (headers internes de tracing Next.js)
 *
 * Rappel : les patterns DOM (React) et CSS (Tailwind) restent détectables
 * par un scanner — cette contrainte est structurelle et documentée dans
 * PENTEST_COMPLIANCE_AUDIT.md. La reco pentester ciblait explicitement
 * "les bannières de version au niveau du serveur frontal", ce que ce
 * middleware couvre côté Next.js.
 *
 * ⚠️  L'anonymisation du header Server posé par Nginx Azure Container Apps
 * demande une configuration côté Nginx (voir deploy/nginx-security.conf).
 */
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(_request: NextRequest) {
  const response = NextResponse.next();

  // F-08 — écrase la bannière Server
  response.headers.set("server", "MA2E");

  // F-08 — supprime tout header qui expose la stack
  response.headers.delete("x-powered-by");
  response.headers.delete("x-nextjs-cache");
  response.headers.delete("x-nextjs-matched-path");
  response.headers.delete("x-nextjs-prerender");
  response.headers.delete("x-nextjs-stale-time");

  return response;
}

// Applique le middleware à toutes les routes sauf les assets statiques
// (les fichiers /_next/static/* et /favicon.ico n'ont pas besoin d'être
// réécrits et le skip évite un coût runtime inutile).
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
