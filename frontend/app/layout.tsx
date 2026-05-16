import "./globals.css";
import type { Metadata } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import { ConfirmProvider } from "@/components/ConfirmProvider";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["300", "400", "500", "600", "700", "800"],
  display: "swap",
});

const sidebarFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-sidebar",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "MA2E · Plateforme Digitale d'Identification",
  description: "Mutuelle des Agents de l'Eau et de l'Électricité",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${jakarta.variable} ${sidebarFont.variable}`}>
      <body className="font-sans antialiased bg-white text-ink-900">
        <ConfirmProvider>{children}</ConfirmProvider>
      </body>
    </html>
  );
}
