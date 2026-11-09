"use client";
import Link from "next/link";
import Logo from "@/components/Logo";
import { Icon } from "@/components/Icon";

type Props = {
  onNavigate?: () => void;
  /** Ferme le tiroir mobile. */
  onClose?: () => void;
};

/**
 * En-tête FIXE de la sidebar : seul le logo MA2E (à gauche, sur une plaque claire)
 * et, à droite, une bande verte de marque (aucun texte). Le bouton de fermeture
 * (tiroir mobile uniquement) se pose sur la bande verte.
 */
export default function SidebarBrand({ onNavigate, onClose }: Props) {
  return (
    <div className="sa-sidebar__head ma2e-brand">
      <Link
        href="/dossiers"
        className="ma2e-brand__logo"
        onClick={onNavigate}
        aria-label="MA2E — retour au tableau opérationnel"
      >
        <Logo size={48} />
      </Link>
      <div className="ma2e-brand__band" aria-hidden="true">
        <svg className="ma2e-brand__wave" viewBox="0 0 120 56" preserveAspectRatio="none" focusable="false">
          <path d="M0 40 C 20 24, 40 56, 64 38 S 104 20, 120 30 L120 56 L0 56 Z" />
          <path d="M0 26 C 24 10, 44 40, 70 24 S 108 8, 120 16" fill="none" />
        </svg>
      </div>
      <button type="button" className="sa-icon-btn sa-sidebar__close ma2e-brand__close" onClick={onClose} aria-label="Fermer le menu">
        <Icon name="cancel-01" />
      </button>
    </div>
  );
}
