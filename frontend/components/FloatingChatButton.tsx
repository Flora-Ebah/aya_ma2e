"use client";
import Image from "next/image";
import { useState } from "react";
import { Icon } from "@/components/Icon";

/**
 * Accès au chat public (nouvel onglet), placé dans le PIED de la sidebar :
 * avatar de l'assistante + libellé, pleine largeur, plus de bouton flottant.
 */
export default function FloatingChatButton({ onNavigate }: { onNavigate?: () => void }) {
  const [imgError, setImgError] = useState(false);

  return (
    <a
      href="/chat"
      target="_blank"
      rel="noopener"
      className="ma2e-chat-link"
      onClick={onNavigate}
      aria-label="Ouvrir le chat de l'assistante dans un nouvel onglet"
    >
      <span className="ma2e-chat-link__avatar" aria-hidden="true">
        {!imgError ? (
          <Image src="/assistant-avatar.png" alt="" width={36} height={36} onError={() => setImgError(true)} />
        ) : (
          <Icon name="message-01" size={20} />
        )}
      </span>
      <span className="ma2e-chat-link__label">Ouvrir le chat</span>
      <Icon name="arrow-up-right-01" size={16} className="ma2e-chat-link__go" />
    </a>
  );
}
