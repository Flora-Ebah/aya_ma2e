"use client";
import { useId } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { Button } from "./Button";
import { IconButton } from "./IconButton";
import { cx } from "./util";
import { useMounted, useModalDialog } from "./dialogs";

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  /** Boutons d'action de l'en-tête (export, impression…), avant « Fermer ». */
  actions?: ReactNode;
  children: ReactNode;
  /**
   * `fullscreen` (défaut) : tiroir plein écran, bouton « Fermer » dans l'en-tête
   * (« Afficher plus », grands tableaux). `side` : panneau latéral droit
   * (filtres, aperçu) avec pied d'actions.
   */
  variant?: "fullscreen" | "side";
  /** Pied d'actions (variante `side`). */
  footer?: ReactNode;
  className?: string;
};

/**
 * Tiroir : remplace la modale pour les contenus volumineux. Plein écran par
 * défaut (en-tête titre + actions + Fermer, corps défilant). `<dialog>` natif :
 * focus piégé, Échap, focus rendu au déclencheur.
 *
 *   <Drawer open={o} onClose={close} title="Tous les dossiers">…</Drawer>
 */
export function Drawer(props: Props) {
  const mounted = useMounted();
  if (!props.open || !mounted) return null;
  return createPortal(<DrawerInner {...props} />, document.body);
}

function DrawerInner({ onClose, title, subtitle, actions, children, variant = "fullscreen", footer, className }: Props) {
  const ref = useModalDialog({ onClose, initialFocus: "none" });
  const id = useId();

  if (variant === "side") {
    return (
      <dialog
        ref={ref}
        className={cx("sa-drawer", className)}
        aria-labelledby={`${id}-t`}
        onClick={(e) => {
          if (e.target === ref.current) onClose();
        }}
      >
        <div className="sa-drawer__header">
          <h2 className="sa-drawer__title" id={`${id}-t`}>
            {title}
          </h2>
          <IconButton icon="cancel-01" label="Fermer" tooltip={false} onClick={onClose} />
        </div>
        <div className="sa-drawer__body">{children}</div>
        {footer && <div className="sa-drawer__footer">{footer}</div>}
      </dialog>
    );
  }

  return (
    <dialog ref={ref} className={cx("sa-tiroir", className)} aria-labelledby={`${id}-t`}>
      <div className="sa-tiroir__entete">
        <div className="sa-tiroir__titre">
          <h2 id={`${id}-t`} className="sa-h4">
            {title}
          </h2>
          {subtitle && <div className="sa-body-sm sa-text-soft">{subtitle}</div>}
        </div>
        <div className="sa-tiroir__actions">
          {actions}
          <Button icon="cancel-01" onClick={onClose} autoFocus>
            Fermer
          </Button>
        </div>
      </div>
      <div className="sa-tiroir__corps">{children}</div>
    </dialog>
  );
}
