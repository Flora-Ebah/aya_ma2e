import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

type Props = {
  /** Nom d'icône du sprite (défaut `inbox`) ou élément React. */
  icon?: string | ReactNode;
  title: string;
  description?: ReactNode;
  /** Bouton(s) d'action (un seul primaire). */
  action?: ReactNode;
  compact?: boolean;
  className?: string;
};

/**
 * État vide : icône 40 px, titre, texte, action.
 *   <EmptyState icon="folder-01" title="Aucun dossier" description="Modifiez les filtres." action={<Button>Réinitialiser</Button>} />
 */
export function EmptyState({ icon = "inbox", title, description, action, compact, className }: Props) {
  return (
    <div className={cx("sa-empty", compact && "sa-empty--compact", className)}>
      <div className="sa-empty__icon">{typeof icon === "string" ? <Icon name={icon} size={40} /> : icon}</div>
      <p className="sa-empty__title">{title}</p>
      {description && <p className="sa-empty__text">{description}</p>}
      {action && <div className="sa-empty__actions">{action}</div>}
    </div>
  );
}
