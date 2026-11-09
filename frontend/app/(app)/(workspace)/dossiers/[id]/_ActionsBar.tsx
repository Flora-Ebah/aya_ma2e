"use client";
import { useEffect, useRef, useState } from "react";
import { STATUS_LABELS } from "@/lib/api";
import { Icon } from "@/components/Icon";

type Props = {
  dossier: any;
  canValidate: boolean;
  canAnonymize: boolean;
  actionLoading: boolean;
  onValidate: () => void;
  onOpenComplement: () => void;
  onOpenReject: () => void;
  onOpenAnonymize: () => void;
};

/**
 * Barre d'actions du dossier (en-tête de page) : 1 action primaire (Valider),
 * 2 actions secondaires (complément, rejet) et un menu « ⋯ » pour l'anonymisation (DPO).
 */
export default function ActionsBar({
  dossier, canValidate, canAnonymize, actionLoading,
  onValidate, onOpenComplement, onOpenReject, onOpenAnonymize,
}: Props) {
  const canAct = dossier.status === "soumis" || dossier.status === "en_validation";
  const enabled = canAct && canValidate && !actionLoading;
  const reason = !canValidate
    ? "Vous n'avez pas la permission de valider ce dossier."
    : !canAct
      ? `Aucune action possible — dossier au statut « ${STATUS_LABELS[dossier.status] || dossier.status} ».`
      : "";

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="sa-page-actions">
        <button type="button" className="sa-btn sa-btn--primary" onClick={onValidate} disabled={!enabled}>
          <Icon name="checkmark-circle-02" className="i" />
          Valider
        </button>
        <button type="button" className="sa-btn sa-btn--outline" onClick={onOpenComplement} disabled={!enabled}>
          <Icon name="refresh" className="i" />
          Complément
        </button>
        <button
          type="button" className="sa-btn sa-btn--outline" onClick={onOpenReject} disabled={!enabled}
          style={enabled ? { color: "rgb(var(--color-status-error))", borderColor: "rgb(var(--color-status-error))" } : undefined}
        >
          <Icon name="cancel-circle" className="i" />
          Rejeter
        </button>
        {canAnonymize && <MoreMenu disabled={actionLoading} onAnonymize={onOpenAnonymize} />}
      </div>
      {reason && <p className="sa-help" style={{ margin: 0 }}>{reason}</p>}
    </div>
  );
}

function MoreMenu({ disabled, onAnonymize }: { disabled: boolean; onAnonymize: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="sa-popover-anchor" ref={ref}>
      <button
        type="button" className="sa-icon-btn sa-icon-btn--outline"
        aria-haspopup="menu" aria-expanded={open} aria-label="Autres actions"
        disabled={disabled} onClick={() => setOpen((v) => !v)}
      >
        <Icon name="more-horizontal" className="i" />
      </button>
      {open && (
        <div className="sa-menu" role="menu" style={{ width: 260 }}>
          <button
            type="button" role="menuitem" className="sa-menu__item sa-menu__item--danger"
            title="Droit à l'oubli ARTCI art. 21 — réservé DPO"
            onClick={() => { setOpen(false); onAnonymize(); }}
          >
            <Icon name="lock-key" className="i" />
            Anonymiser ce dossier (DPO)
          </button>
        </div>
      )}
    </div>
  );
}
