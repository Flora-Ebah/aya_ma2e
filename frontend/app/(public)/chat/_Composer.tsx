"use client";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import { Alert } from "@/components/ui/Alert";
import { IconButton } from "@/components/ui/IconButton";
import type { PendingFile } from "./_utils";

type Props = {
  input: string;
  hasMessages: boolean;
  loading: boolean;
  error: string | null;
  pendingFile: PendingFile | null;
  onInputChange: (v: string) => void;
  onSubmit: () => void;
  onFilePick: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPendingFileRemove: () => void;
  /** Le bot attend une sélection via un formulaire rendu dans la bulle
   *  (select/options). Bloque la saisie libre pour éviter la confusion. */
  awaitingForm?: boolean;
};

/** Barre de saisie : textarea auto-resize + upload + envoi. */
export default function Composer({
  input, hasMessages, loading, error, pendingFile,
  onInputChange, onSubmit, onFilePick, onPendingFileRemove,
  awaitingForm,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const attachBtnWrapRef = useRef<HTMLDivElement>(null);
  const [attachOpen, setAttachOpen] = useState(false);

  useEffect(() => {
    if (!loading) textareaRef.current?.focus();
  }, [loading]);

  useEffect(() => {
    if (!attachOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (
        attachBtnWrapRef.current &&
        !attachBtnWrapRef.current.contains(e.target as Node)
      ) {
        setAttachOpen(false);
      }
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setAttachOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEsc);
    };
  }, [attachOpen]);

  function autoResize() {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    onSubmit();
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className={hasMessages ? "chat-composer chat-composer--sticky" : "chat-composer"}>
      <div className="chat-wrap">
        {error && (
          <div style={{ marginBottom: 8 }}>
            <Alert tone="error" compact>{error}</Alert>
          </div>
        )}
        <form onSubmit={handleSubmit} className={`chat-box${awaitingForm ? " chat-box--locked" : ""}`}>
          {pendingFile && <PendingFilePreview file={pendingFile} onRemove={onPendingFileRemove} />}
          {awaitingForm && (
            <div className="chat-box__hint" role="note">
              <Icon name="arrow-up-02" size={14} />
              Choisissez une option dans le message ci-dessus pour continuer.
            </div>
          )}
          <input ref={fileInputRef} type="file" accept="image/*" onChange={onFilePick} className="sa-sr-only" tabIndex={-1} aria-hidden="true" />
          <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" onChange={onFilePick} className="sa-sr-only" tabIndex={-1} aria-hidden="true" />
          <label className="sa-sr-only" htmlFor="chat-input">Votre message</label>
          <textarea
            id="chat-input"
            ref={textareaRef}
            value={input}
            onChange={(e) => { onInputChange(e.target.value); autoResize(); }}
            onKeyDown={onKeyDown}
            rows={1}
            disabled={loading || awaitingForm}
            placeholder={
              awaitingForm
                ? "Sélectionnez une option ci-dessus…"
                : "Comment puis-je vous aider aujourd'hui ?"
            }
            className="chat-box__input"
            autoFocus
          />
          <div className="chat-box__bar">
            <div
              ref={attachBtnWrapRef}
              style={{ position: "relative", display: "inline-block" }}
            >
              <IconButton
                icon="attachment-01"
                variant="outline"
                label="Ajouter une image"
                onClick={() => setAttachOpen((v) => !v)}
                disabled={loading || pendingFile?.uploading || awaitingForm}
                aria-expanded={attachOpen}
                aria-haspopup="menu"
              />
              {attachOpen && (
                <div
                  role="menu"
                  style={{
                    position: "absolute",
                    bottom: "calc(100% + 8px)",
                    left: 0,
                    background: "rgb(var(--color-bg-surface))",
                    border: "1px solid rgb(var(--color-border-default))",
                    borderRadius: 12,
                    boxShadow: "0 12px 32px -8px rgba(0,0,0,0.35)",
                    padding: 6,
                    minWidth: 220,
                    zIndex: 50,
                  }}
                >
                  <AttachMenuItem
                    icon="camera-01"
                    label="Prendre une photo"
                    hint="Caméra arrière"
                    onClick={() => {
                      setAttachOpen(false);
                      cameraInputRef.current?.click();
                    }}
                  />
                  <AttachMenuItem
                    icon="image-01"
                    label="Télécharger une image"
                    hint="Galerie / fichiers"
                    onClick={() => {
                      setAttachOpen(false);
                      fileInputRef.current?.click();
                    }}
                  />
                </div>
              )}
            </div>
            <IconButton
              icon="arrow-up-02"
              variant="primary"
              label="Envoyer"
              type="submit"
              tooltip={false}
              disabled={loading || pendingFile?.uploading || awaitingForm || (!input.trim() && !pendingFile?.url)}
            />
          </div>
        </form>
        <ComposerFooter />
      </div>
    </div>
  );
}

function AttachMenuItem({
  icon,
  label,
  hint,
  onClick,
}: {
  icon: string;
  label: string;
  hint: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        padding: "10px 10px",
        background: "transparent",
        border: 0,
        borderRadius: 8,
        cursor: "pointer",
        textAlign: "left",
        color: "inherit",
      }}
      onMouseEnter={(e) =>
        ((e.currentTarget as HTMLButtonElement).style.background =
          "rgb(var(--color-bg-subtle))")
      }
      onMouseLeave={(e) =>
        ((e.currentTarget as HTMLButtonElement).style.background = "transparent")
      }
    >
      <span
        className="sa-icon-tile sa-icon-tile--accent"
        aria-hidden="true"
        style={{ width: 32, height: 32 }}
      >
        <Icon name={icon} />
      </span>
      <span style={{ minWidth: 0 }}>
        <span className="sa-strong" style={{ display: "block", fontSize: 14 }}>
          {label}
        </span>
        <span className="sa-body-sm sa-text-soft" style={{ display: "block" }}>
          {hint}
        </span>
      </span>
    </button>
  );
}

function PendingFilePreview({ file, onRemove }: { file: PendingFile; onRemove: () => void }) {
  return (
    <div className="chat-file">
      <span className="sa-icon-tile" aria-hidden="true">
        <Icon name={file.type.startsWith("image/") ? "image-01" : "attachment-01"} />
      </span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div className="sa-strong" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</div>
        <div className="sa-body-sm sa-text-soft">
          {file.uploading ? "Envoi en cours…" : `${(file.size / 1024).toFixed(1)} Ko · prêt`}
        </div>
      </div>
      <IconButton icon="cancel-01" label="Retirer le fichier" tooltip={false} onClick={onRemove} />
    </div>
  );
}

function ComposerFooter() {
  return (
    <div className="chat-foot">
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Icon name="shield-user" size={14} />
        <span className="sa-hide-mobile">L&apos;assistant peut commettre des erreurs. Vérifiez les informations.</span>
        <span className="sa-show-mobile">Conforme loi 2013-450</span>
      </span>
      <span className="sa-hide-mobile">
        <kbd className="sa-kbd">Shift + Entrée</kbd> pour saut de ligne
      </span>
    </div>
  );
}
