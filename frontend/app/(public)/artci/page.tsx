"use client";
import Link from "next/link";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { ButtonLink } from "@/components/ui/Button";
import ContactForm from "./_ContactForm";
import { DpoContactSection, InfoCardsSection, RightsSection } from "./_LegalSections";

// Page publique conforme WCAG 2.2 niveau AA :
// - lang="fr" hérité du root layout
// - structure landmarks (header, nav, main, footer) + lien d'évitement
// - icônes décoratives en aria-hidden
// - champs étiquetés, erreurs liées par aria-describedby
export default function ArtciPage() {
  return (
    <div className="ma2e-public">
      <a href="#main-content" className="sa-skip-link">
        Aller au contenu principal
      </a>

      <header className="ma2e-public__bar" role="banner">
        <Link href="/" className="ma2e-public__brand" aria-label="Accueil MA2E">
          <Logo size={32} />
          <span className="sa-strong">MA2E</span>
        </Link>
        <nav aria-label="Navigation publique" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ThemeToggle />
          <ButtonLink href="/chat" variant="outline" size="sm" icon="message-01">
            Revenir au chat
          </ButtonLink>
        </nav>
      </header>

      <main id="main-content" className="ma2e-public__content" tabIndex={-1}>
        <div>
          <p className="sa-header__eyebrow">Protection des données — Loi 2013-450 (ARTCI)</p>
          <h1 className="sa-page-title" id="titre-page">Vos données, vos droits</h1>
          <p className="sa-page-desc" style={{ maxWidth: 720 }}>
            Cette page vous explique comment MA2E (Mutuelle des Agents de l&apos;Eau et de
            l&apos;Électricité) collecte, traite et protège vos données personnelles,
            conformément à la loi ivoirienne n° 2013-450 sur la protection des données à
            caractère personnel.
          </p>
        </div>

        <InfoCardsSection />
        <RightsSection />
        <DpoContactSection />
        <ContactForm />
      </main>

      <footer className="ma2e-public__foot" role="contentinfo">
        <span>MA2E — Mutuelle des Agents de l&apos;Eau et de l&apos;Électricité</span>
        <span>Dernière mise à jour : 15 juin 2026 · Conforme loi 2013-450 et recommandations ARTCI</span>
      </footer>
    </div>
  );
}
