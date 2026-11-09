"use client";
import { useId } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/components/Icon";
import { IconButton } from "./IconButton";
import { cx } from "./util";
import { useMounted, useModalDialog } from "./dialogs";

type Props = {
  /** Rien n'est rendu si false. */
  open: boolean;
  /** Fermeture (croix, Échap, clic sur le fond). */
  onClose: () => void;
  title: string;
  subtitle?: string;
  /** Nom d'icône du sprite affiché dans une tuile à gauche du titre. */
  icon?: string;
  /** Tuile d'icône rouge (confirmation destructive). */
  danger?: boolean;
  children: ReactNode;
  /** Boutons du pied (alignés à droite ; le dernier est le primaire). */
  footer?: ReactNode;
  /** `sm` ≈ 400 px (confirmation), `md` ≈ 560 px (défaut), `lg` ≈ 800 px+. `xl` = alias de `lg`. */
  size?: "sm" | "md" | "lg" | "xl";
  /** Interdit la fermeture au clic sur le fond (saisie en cours). */
  persistent?: boolean;
  className?: string;
};

/**
 * Modale du design system (`<dialog>` natif : focus piégé, Échap, pile unique).
 * Réservée aux **petits formulaires et confirmations** — aucune barre de
 * défilement : si le contenu est long, utiliser une page de détail ou un
 * `Drawer` plein écran.
 *
 *   <Modal open={o} onClose={close} title="Renommer" footer={<><Button variant="secondary" onClick={close}>Annuler</Button><Button onClick={save}>Enregistrer</Button></>}>
 *     <Field label="Nom"><Input … /></Field>
 *   </Modal>
 */
export function Modal(props: Props) {
  const mounted = useMounted();
  if (!props.open || !mounted) return null;
  return createPortal(<ModalInner {...props} />, document.body);
}

function ModalInner({ onClose, title, subtitle, icon, danger, children, footer, size = "md", persistent, className }: Props) {
  const ref = useModalDialog({ onClose });
  const id = useId();
  return (
    <dialog
      ref={ref}
      className={cx("sa-dialog", size === "sm" && "sa-dialog--sm", (size === "lg" || size === "xl") && "sa-dialog--lg", className)}
      aria-labelledby={`${id}-t`}
      onClick={(e) => {
        if (e.target === ref.current && !persistent) onClose();
      }}
    >
      <div className="sa-dialog__header">
        {icon && (
          <span className={cx("sa-icon-tile", danger && "sa-icon-tile--error")}>
            <Icon name={icon} />
          </span>
        )}
        <div className="sa-dialog__heading">
          <h2 className="sa-dialog__title" id={`${id}-t`}>
            {title}
          </h2>
          {subtitle && <div className="sa-dialog__subtitle">{subtitle}</div>}
        </div>
        <IconButton icon="cancel-01" label="Fermer" tooltip={false} onClick={onClose} />
      </div>
      <div className="sa-dialog__body">{children}</div>
      {footer && (
        <div className="sa-dialog__footer" data-dialog-footer>
          {footer}
        </div>
      )}
    </dialog>
  );
}
