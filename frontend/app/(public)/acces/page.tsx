"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { Button } from "@/components/ui/Button";

const WHATSAPP_NUMBER =
  process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || "22587137512";
const WHATSAPP_PRESET = encodeURIComponent(
  "Bonjour, je suis sociétaire MA2E."
);

/** Choix du canal (WhatsApp / chat web) — page publique d'une seule fenêtre. */
export default function AccesPage() {
  const router = useRouter();
  const [chosen, setChosen] = useState<"whatsapp" | "web" | null>(null);

  function pickWhatsApp() {
    setChosen("whatsapp");
    window.location.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${WHATSAPP_PRESET}`;
  }

  function pickWeb() {
    setChosen("web");
    router.push("/chat");
  }

  return (
    <div className="ma2e-public">
      <header className="ma2e-public__bar">
        <div className="ma2e-public__brand">
          <Logo size={32} />
          <span className="sa-strong">MA2E</span>
          <span className="sa-text-soft sa-body-sm">· Espace sociétaire</span>
        </div>
        <ThemeToggle />
      </header>

      <main id="contenu" className="ma2e-public__main" tabIndex={-1}>
        <div className="ma2e-public__hero">
          <div className="ma2e-public__avatar">
            <Image src="/assistant.png" alt="" width={176} height={176} priority />
          </div>
          <h1 className="sa-h2" id="titre-page">
            Bonjour, je suis votre assistant MA2E.
          </h1>
          <p className="sa-body sa-text-soft">
            M&apos;identifier · Mettre à jour mes informations · Suivre mon dossier.
            <br />
            Choisissez votre canal pour commencer.
          </p>

          <div className="ma2e-public__actions">
            <Button size="lg" block icon="whatsapp" loading={chosen === "whatsapp"} disabled={chosen !== null} onClick={pickWhatsApp}>
              Ouvrir WhatsApp
            </Button>
            <Button size="lg" block variant="outline" icon="message-01" loading={chosen === "web"} disabled={chosen !== null} onClick={pickWeb}>
              Ouvrir le chat web
            </Button>
          </div>

          <p className="sa-body-sm sa-text-soft">
            <span className="sa-strong">Loi 2013-450</span> · TLS 1.3 · Audit HMAC-SHA256
          </p>
        </div>
      </main>

      <footer className="ma2e-public__foot">
        <span>© MA2E · Mutuelle des agents de l&apos;eau et de l&apos;électricité</span>
        <nav aria-label="Informations légales" style={{ display: "flex", gap: 16 }}>
          <Link className="sa-link" href="/artci">Mentions légales</Link>
          <Link className="sa-link" href="/artci">Confidentialité</Link>
        </nav>
      </footer>
    </div>
  );
}
