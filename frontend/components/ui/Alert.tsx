import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

export type AlertTone = "info" | "success" | "warning" | "error" | "brand";
const ICON: Record<AlertTone, string> = {
  info: "information-circle",
  success: "checkmark-circle-02",
  warning: "alert-02",
  error: "alert-circle",
  brand: "information-circle",
};

type Props = {
  tone?: AlertTone;
  title?: ReactNode;
  children?: ReactNode;
  /** Boutons / liens d'action sous le texte. */
  actions?: ReactNode;
  compact?: boolean;
  className?: string;
};

/**
 * Alerte en ligne (icône + texte, jamais la couleur seule). `error` → `role="alert"`.
 *   <Alert tone="warning" title="Session bientôt expirée">Reconnectez-vous pour continuer.</Alert>
 */
export function Alert({ tone = "info", title, children, actions, compact, className }: Props) {
  return (
    <div className={cx("sa-alert", `sa-alert--${tone}`, compact && "sa-alert--compact", className)} role={tone === "error" ? "alert" : "status"}>
      <Icon name={ICON[tone]} />
      <div className="sa-alert__body">
        {title && <p className="sa-alert__title">{title}</p>}
        {children && <div className="sa-alert__text">{children}</div>}
        {actions && <div className="sa-alert__actions">{actions}</div>}
      </div>
    </div>
  );
}
