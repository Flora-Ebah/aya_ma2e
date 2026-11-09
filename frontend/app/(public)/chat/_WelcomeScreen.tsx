"use client";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Icon";
import AssistantAvatar from "./_AssistantAvatar";
import { TENANT_SLUG } from "./_utils";

type ParcoursCard = {
  code: string;
  label: string;
  emoji: string;
  description: string | null;
  position: number;
  start_payload: string;
};

type Props = {
  hello: string;
  avatarOk: boolean;
  /** payload = ce qui est envoyé au backend (ex. "1"), display = ce qui est
   *  affiché dans la bulle utilisateur (ex. "Mise à jour de compte"). */
  onPick: (payload: string, display?: string) => void;
  disabled: boolean;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

// Associe un emoji à un code HugeIcons pour les cartes.
function iconForLabel(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("inscr")) return "user-add-01";
  if (l.includes("modif") || l.includes("mise")) return "edit-01";
  if (l.includes("consult") || l.includes("vérif") || l.includes("verif")) return "activity-01";
  if (l.includes("question") || l.includes("chat") || l.includes("faq")) return "message-01";
  return "arrow-right-02";
}

export default function WelcomeScreen({ hello, avatarOk, onPick, disabled }: Props) {
  const [cards, setCards] = useState<ParcoursCard[] | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const totalCards = (cards?.length ?? 0) + (cards !== null ? 1 : 0);
  const centered = totalCards <= 1;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/webhooks/web/${TENANT_SLUG}/parcours`);
        if (!res.ok) throw new Error(String(res.status));
        const data: ParcoursCard[] = await res.json();
        if (!cancelled) setCards(data);
      } catch (e: any) {
        if (!cancelled) setLoadErr(e?.message ?? "fetch failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const wrapStyle: React.CSSProperties = {
    paddingTop: 24,
    paddingBottom: 12,
    ...(centered
      ? { textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center" }
      : {}),
  };

  return (
    <div className="chat-wrap" style={wrapStyle}>
      <div style={{ marginBottom: 16 }}>
        <AssistantAvatar size={56} avatarOk={avatarOk} ring />
      </div>

      <h1 className="sa-h2" id="titre-page" style={{ marginBottom: 20 }}>
        {hello},<br />
        Comment puis-je vous aider&nbsp;?
      </h1>

      {(() => {
        const quickStyle: React.CSSProperties = centered
          ? {
              display: "flex",
              justifyContent: "center",
              width: "100%",
            }
          : {};
        return (
          <div className="chat-quick" style={quickStyle}>
            {cards === null && !loadErr && (
              <>
                <QuickActionSkeleton />
                <QuickActionSkeleton />
              </>
            )}

            {cards?.map((c, i) => (
              <QuickAction
                key={c.code}
                primary={i === 0}
                disabled={disabled}
                icon={iconForLabel(c.label)}
                title={c.label}
                subtitle={c.description || "Démarrer le parcours"}
                onClick={() => onPick(c.start_payload, c.label)}
                fullWidth={centered}
              />
            ))}

            {/* Toujours proposer la question libre, même sans parcours. */}
            {cards !== null && (
              <QuickAction
                primary={cards.length === 0}
                disabled={disabled}
                icon="message-01"
                title="Poser une question"
                subtitle="Interroger l'assistante en texte libre"
                onClick={() => onPick("J'ai une question", "J'ai une question")}
                fullWidth={centered}
              />
            )}
          </div>
        );
      })()}

      {loadErr && (
        <div className="sa-text-soft" style={{ marginTop: 8, fontSize: 13 }}>
          Impossible de charger les parcours ({loadErr}). Vous pouvez quand même écrire ci-dessous.
        </div>
      )}
    </div>
  );
}

function QuickAction({
  primary,
  disabled,
  icon,
  title,
  subtitle,
  onClick,
  fullWidth,
}: {
  primary?: boolean;
  disabled: boolean;
  icon: string;
  title: string;
  subtitle: string;
  onClick: () => void;
  fullWidth?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`sa-card sa-card--interactive chat-quick__btn${primary ? " is-primary" : ""}`}
      style={{ borderRadius: 9999, ...(fullWidth ? { width: "100%", maxWidth: 420 } : {}) }}
    >
      <span className={`sa-icon-tile${primary ? "" : " sa-icon-tile--accent"}`} aria-hidden="true">
        <Icon name={icon} />
      </span>
      <span style={{ minWidth: 0 }}>
        <span className="sa-strong" style={{ display: "block" }}>{title}</span>
      </span>
    </button>
  );
}

function QuickActionSkeleton() {
  return (
    <div
      className="sa-card"
      style={{
        padding: 16,
        display: "flex",
        gap: 12,
        alignItems: "center",
        opacity: 0.6,
      }}
      aria-hidden="true"
    >
      <div
        className="sa-skeleton"
        style={{ width: 40, height: 40, borderRadius: 10 }}
      />
      <div style={{ flex: 1 }}>
        <div className="sa-skeleton sa-skeleton--text" style={{ width: "40%", height: 14 }} />
        <div className="sa-skeleton sa-skeleton--text" style={{ width: "70%", height: 12, marginTop: 6 }} />
      </div>
    </div>
  );
}
