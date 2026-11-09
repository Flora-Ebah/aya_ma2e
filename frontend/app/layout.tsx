import "./globals.css";
import type { Metadata } from "next";
import { ConfirmProvider } from "@/components/ConfirmProvider";
import { CurrentUserProvider } from "@/components/CurrentUserProvider";
import { IconSprite } from "@/components/IconSprite";
import { THEME_INIT_SCRIPT } from "@/lib/theme-script";

/**
 * Polices GS2E (identité visuelle) chargées via <link> côté client :
 *   - Outfit : UI de base (texte, boutons, formulaires)   → --font-outfit
 *   - Sora   : titres de section                          → --font-sora
 *   - JetBrains Mono : chiffres techniques                → --font-jetbrains-mono
 *
 * `next/font/google` nécessite un fetch réseau au build (fonts.googleapis.com)
 * que l'environnement de prod Azure bloque ; on passe donc par un <link> HTML
 * classique — même rendu visuel, build offline-safe.
 * Les variables CSS sont définies dans `globals.css`.
 */

export const metadata: Metadata = {
  title: "MA2E · Plateforme Digitale d'Identification",
  description: "Mutuelle des Agents de l'Eau et de l'Électricité — Groupe GS2E",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="fr"
      data-theme="light"
      suppressHydrationWarning
    >
      <head>
        {/* Google Fonts — chargement runtime (le build n'a pas accès au réseau) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        {/* Thème clair / sombre / système appliqué avant le premier rendu (pas de flash) */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans antialiased bg-canvas text-ink">
        {/* Sprite SVG HugeIcons injecté une seule fois pour que <Icon> le référence via <use> */}
        <IconSprite />
        <CurrentUserProvider>
          <ConfirmProvider>{children}</ConfirmProvider>
        </CurrentUserProvider>
      </body>
    </html>
  );
}
