"use client";
import type { RefObject } from "react";
import { Icon } from "@/components/Icon";
import AssistantAvatar from "./_AssistantAvatar";
import ChatForm from "./_ChatForm";
import SignaturePad from "./_SignaturePad";
import { renderText, type ChatMessage } from "./_utils";

type Props = {
  messages: ChatMessage[];
  loading: boolean;
  avatarOk: boolean;
  bottomRef: RefObject<HTMLDivElement>;
  sessionId: string;
  onFormSubmit?: (messageId: string, payload: string, displayText: string) => void;
  onFormSubmitMedia?: (messageId: string, mediaUrl: string, displayText: string) => void;
  onFormEscape?: (messageId: string) => void;
};

export default function Transcript({
  messages, loading, avatarOk, bottomRef, sessionId,
  onFormSubmit, onFormSubmitMedia, onFormEscape,
}: Props) {
  return (
    <div className="chat-scroll">
      <div className="chat-wrap chat-list" role="log" aria-live="polite" aria-label="Conversation">
        {messages.map((m, idx) => (
          <MessageBubble
            key={m.id}
            message={m}
            previous={messages[idx - 1]}
            avatarOk={avatarOk}
            sessionId={sessionId}
            onFormSubmit={onFormSubmit}
            onFormSubmitMedia={onFormSubmitMedia}
            onFormEscape={onFormEscape}
          />
        ))}
        {loading && (
          <div className="chat-row animate-fade-in" role="status" aria-label="L'assistante écrit">
            <AssistantAvatar size={32} avatarOk={avatarOk} ring={false} />
            <div className="chat-bubble chat-bubble--in">
              <Dots />
            </div>
          </div>
        )}
        <div ref={bottomRef} aria-hidden className="h-1" />
      </div>
    </div>
  );
}

function stripOptionsBlock(text: string): string {
  // Retire le bloc "1. Mlle\n2. Mme\n..." quand on rend le form à la place.
  const lines = text.split(/\n/);
  const firstOpt = lines.findIndex((l) => /^\s*\d{1,2}\.\s+\S/.test(l));
  if (firstOpt < 0) return text;
  return lines.slice(0, firstOpt).join("\n").trimEnd();
}

/**
 * Pour les messages portant un `ui.type === "form"`, le texte contient encore
 * le modèle à copier-coller (« Étape 1 — copiez le modèle… Nom : … »). Comme
 * on rend maintenant les champs comme vrai formulaire, on vire ces paragraphes
 * pour ne garder que l'intro utile (éventuelle) et le rappel d'échappement.
 */
function stripFormTemplate(text: string): string {
  const paragraphs = text.split(/\n\s*\n/);
  const kept = paragraphs.filter((p) => {
    const trimmed = p.trim();
    if (!trimmed) return false;
    // Intro d'explication du copier-coller : à supprimer.
    if (/copiez le mod[eè]le|remplissez-le|renvoyez-le|un seul message/i.test(trimmed)) {
      return false;
    }
    // Paragraphe qui est un modèle (≥ 2 lignes finissant par " :")
    const lines = trimmed.split(/\n/);
    const labelLines = lines.filter((l) => /:\s*$/.test(l.trim())).length;
    if (labelLines >= 2 && labelLines >= Math.ceil(lines.length * 0.6)) {
      return false;
    }
    return true;
  });
  return kept.join("\n\n").trim();
}

/** Rappel textuel MENU/STOP/ANNULER remplacé par le bouton « Annuler et
 *  recommencer » dans la carte formulaire → on l'enlève du corps du message. */
function stripEscapeHint(text: string): string {
  return text
    .split(/\n\s*\n/)
    .filter((p) => !/\b(MENU|STOP|ANNULER|RECOMMENCER)\b.*reprendre/i.test(p.trim()))
    .join("\n\n")
    .trim();
}

function MessageBubble({
  message, previous, avatarOk, sessionId,
  onFormSubmit, onFormSubmitMedia, onFormEscape,
}: {
  message: ChatMessage;
  previous?: ChatMessage;
  avatarOk: boolean;
  sessionId: string;
  onFormSubmit?: (messageId: string, payload: string, displayText: string) => void;
  onFormSubmitMedia?: (messageId: string, mediaUrl: string, displayText: string) => void;
  onFormEscape?: (messageId: string) => void;
}) {
  const isOut = message.direction === "out";
  const sameAuthor = previous?.direction === message.direction;
  const time = new Date(message.timestamp).toLocaleTimeString("fr-FR", {
    hour: "2-digit", minute: "2-digit",
  });

  if (isOut) {
    const hasUi = !!message.ui;
    let bodyText = message.text;
    if (hasUi) {
      bodyText = stripOptionsBlock(bodyText);
      bodyText = stripEscapeHint(bodyText);
      if (message.ui?.type === "form") {
        bodyText = stripFormTemplate(bodyText);
      }
    }
    // Après soumission d'un form, on remplace la carte formulaire par un
    // résumé read-only (titre + description) pour que l'utilisateur garde le
    // contexte de la question dans l'historique.
    const answeredRecap =
      hasUi && message.uiAnswered
        ? (() => {
            const u = message.ui!;
            const t =
              u.type === "form"
                ? (u.title || "")
                : u.type === "select"
                ? u.label
                : (u.title || "Signature");
            return {
              title: t.trim(),
              description: (u.description || "").trim(),
            };
          })()
        : null;

    // Bulle bot entièrement vide (texte "…" ou vide ET pas de formulaire actif
    // ET pas de résumé read-only à afficher) → masquer.
    const normalized = (bodyText || "").trim();
    const isEmptyGhost =
      (!normalized || normalized === "…") &&
      (!hasUi || message.uiAnswered) &&
      !answeredRecap?.title && !answeredRecap?.description;
    if (isEmptyGhost) return null;
    return (
      <div className="chat-row animate-slide-up">
        {!sameAuthor ? <AssistantAvatar size={32} avatarOk={avatarOk} ring={false} /> : <span style={{ width: 32, flex: "none" }} />}
        <div className={`chat-bubble chat-bubble--in${hasUi && !message.uiAnswered ? " chat-bubble--form" : ""}`}>
          {!sameAuthor && <div className="sa-strong" style={{ marginBottom: 4 }}>MA2E Assistant</div>}
          {bodyText && !answeredRecap && (
            // Reste utile même avec un form actif : porte les messages d'erreur
            // de validation côté backend (« Matricule invalide… ») au moment
            // du re-prompt. Le template lui-même est déjà stripped plus haut.
            <div className="chat-text">{renderText(bodyText)}</div>
          )}
          {answeredRecap && (answeredRecap.title || answeredRecap.description) && (
            <div className="chat-recap">
              {answeredRecap.title && (
                <div className="chat-recap__title">{answeredRecap.title}</div>
              )}
              {answeredRecap.description && (
                <div className="chat-recap__desc">{answeredRecap.description}</div>
              )}
            </div>
          )}
          {hasUi && !message.uiAnswered && message.ui!.type === "signature" && onFormSubmitMedia && (
            <SignaturePad
              sessionId={sessionId}
              title={message.ui!.title}
              description={message.ui!.description}
              disabled={false}
              onSubmit={(url, display) => onFormSubmitMedia(message.id, url, display)}
              onEscape={onFormEscape ? () => onFormEscape(message.id) : undefined}
            />
          )}
          {hasUi && !message.uiAnswered && message.ui!.type !== "signature" && onFormSubmit && (
            <ChatForm
              ui={message.ui!}
              disabled={false}
              onSubmit={(payload, display) => onFormSubmit(message.id, payload, display)}
              onEscape={onFormEscape ? () => onFormEscape(message.id) : undefined}
            />
          )}
          <div className="chat-time">{time}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-row chat-row--out animate-slide-up">
      <div className="chat-bubble chat-bubble--out">
        <div className="chat-text">{renderText(message.text)}</div>
        <div className="chat-time">
          {time}
          <Icon name="tick-double-01" size={14} />
        </div>
      </div>
    </div>
  );
}

function Dots() {
  return (
    <span className="chat-dots" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}
