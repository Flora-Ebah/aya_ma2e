"use client";
import { useEffect, useId } from "react";
import { Icon } from "@/components/Icon";

/* ============================================================ */
/*  Coque de petite modale (sans barre de défilement)            */
/* ============================================================ */
function ModalShell({ onClose, title, icon, tone = "ok", children, footer }: {
  onClose: () => void;
  title: string;
  icon: string;
  tone?: "ok" | "error" | "warn";
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  const titleId = useId();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    const prev = document.body.style.overflow;
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: "var(--z-modal)" as any,
        background: "rgb(var(--color-bg-overlay) / 0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
      }}
    >
      <div
        className="sa-dialog sa-dialog--static"
        role="dialog" aria-modal="true" aria-labelledby={titleId}
        style={{ maxWidth: 520, maxHeight: "calc(100dvh - 32px)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sa-dialog__header">
          <span className={`sa-icon-tile sa-icon-tile--${tone}`} aria-hidden="true">
            <Icon name={icon} className="i" />
          </span>
          <div className="sa-dialog__heading">
            <h2 className="sa-dialog__title" id={titleId}>{title}</h2>
          </div>
          <button type="button" className="sa-icon-btn" onClick={onClose} aria-label="Fermer">
            <Icon name="cancel-01" className="i" />
          </button>
        </div>
        <div className="sa-dialog__body" style={{ overflowY: "visible" }}>{children}</div>
        <div className="sa-dialog__footer">{footer}</div>
      </div>
    </div>
  );
}

/* ============================================================ */
/*  Rejet                                                         */
/* ============================================================ */
export function RejectModal({
  motive, presets, actionLoading, onMotiveChange, onClose, onSubmit,
}: {
  motive: string;
  presets: string[];
  actionLoading: boolean;
  onMotiveChange: (v: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  return (
    <ModalShell
      onClose={onClose} title="Rejeter le dossier" icon="cancel-circle" tone="error"
      footer={
        <>
          <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
          <button
            type="button" className="sa-btn sa-btn--danger" onClick={onSubmit}
            disabled={actionLoading || !motive.trim()}
          >
            Rejeter
          </button>
        </>
      }
    >
      <p className="sa-help" style={{ margin: 0 }}>
        Le sociétaire sera notifié du rejet et du motif (US-20).
      </p>
      {presets.length > 0 && (
        <div className="sa-field">
          <label className="sa-label" htmlFor="reject-preset">Motif prédéfini</label>
          <select
            id="reject-preset" className="sa-select"
            value={presets.includes(motive) ? motive : ""}
            onChange={(e) => e.target.value && onMotiveChange(e.target.value)}
          >
            <option value="">Choisir un motif…</option>
            {presets.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      )}
      <div className="sa-field">
        <label className="sa-label" htmlFor="reject-motive">Motif transmis au sociétaire</label>
        <textarea
          id="reject-motive" className="sa-textarea" style={{ minHeight: 88 }}
          value={motive} onChange={(e) => onMotiveChange(e.target.value)}
          placeholder="Précisez ou personnalisez le motif…" autoFocus
        />
      </div>
    </ModalShell>
  );
}

/* ============================================================ */
/*  Complément                                                    */
/* ============================================================ */
export function ComplementModal({
  text, actionLoading, onTextChange, onClose, onSubmit,
}: {
  text: string;
  actionLoading: boolean;
  onTextChange: (v: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  return (
    <ModalShell
      onClose={onClose} title="Demander un complément" icon="refresh" tone="warn"
      footer={
        <>
          <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
          <button
            type="button" className="sa-btn sa-btn--primary" onClick={onSubmit}
            disabled={actionLoading || !text.trim()}
          >
            Envoyer
          </button>
        </>
      }
    >
      <p className="sa-help" style={{ margin: 0 }}>
        Le sociétaire recevra la demande sur son canal d&apos;origine.
      </p>
      <div className="sa-field">
        <label className="sa-label" htmlFor="complement-text">Éléments manquants</label>
        <textarea
          id="complement-text" className="sa-textarea" style={{ minHeight: 104 }}
          value={text} onChange={(e) => onTextChange(e.target.value)}
          placeholder="Précisez les éléments manquants…" autoFocus
        />
      </div>
    </ModalShell>
  );
}

/* ============================================================ */
/*  Anonymisation                                                 */
/* ============================================================ */
export function AnonymizeModal({
  reason, actionLoading, onReasonChange, onClose, onSubmit,
}: {
  reason: string;
  actionLoading: boolean;
  onReasonChange: (v: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  return (
    <ModalShell
      onClose={onClose} title="Anonymiser ce dossier (US-28)" icon="lock-key" tone="error"
      footer={
        <>
          <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
          <button
            type="button" className="sa-btn sa-btn--danger" onClick={onSubmit}
            disabled={actionLoading || reason.trim().length < 10}
          >
            Anonymiser
          </button>
        </>
      }
    >
      <div className="sa-alert sa-alert--error" role="alert">
        <Icon name="alert-02" className="i" />
        <div className="sa-alert__body">
          <span className="sa-alert__title">Opération irréversible</span>
          <p className="sa-alert__text" style={{ margin: 0 }}>
            Les données nominatives (nom, photos, contact, OCR…) seront remplacées par des valeurs
            anonymes. Le journal d&apos;audit et les statistiques sont conservés (loi 2013-450, art. 21).
          </p>
        </div>
      </div>
      <div className="sa-field">
        <label className="sa-label" htmlFor="anonymize-reason">
          Motif <span className="sa-label__opt">(consigné pour traçabilité, 10 caractères min.)</span>
        </label>
        <textarea
          id="anonymize-reason" className="sa-textarea" style={{ minHeight: 72 }}
          value={reason} onChange={(e) => onReasonChange(e.target.value)}
          placeholder="Ex : demande du sociétaire reçue par e-mail le …" autoFocus
        />
      </div>
    </ModalShell>
  );
}

/* ============================================================ */
/*  Zoom image                                                    */
/* ============================================================ */
export function ImageZoom({ url, onClose }: { url: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog" aria-modal="true" aria-label="Pièce d'identité en grand"
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: "var(--z-modal)" as any,
        background: "rgb(var(--color-bg-overlay) / 0.85)", cursor: "zoom-out",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 32,
      }}
    >
      <button
        type="button" className="sa-icon-btn sa-icon-btn--primary" onClick={onClose}
        aria-label="Fermer" style={{ position: "absolute", top: 16, right: 16 }}
      >
        <Icon name="cancel-01" className="i" />
      </button>
      <img
        src={url} alt="Pièce d'identité" onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "100%", maxHeight: "100%", borderRadius: "var(--radius-sm)" }}
      />
    </div>
  );
}
