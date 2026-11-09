import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label"> & {
  /** Nom d'icône du sprite. */
  icon: string;
  /** Libellé accessible (obligatoire : le bouton n'a pas de texte). */
  label: string;
  variant?: "default" | "outline" | "primary";
  /** Pastille de notification (point). */
  dot?: boolean;
  /** Affiche aussi le libellé en infobulle (data-tooltip). */
  tooltip?: boolean;
};

/**
 * Bouton icône carré 44 px (cible tactile conforme).
 *   <IconButton icon="cancel-01" label="Fermer" onClick={…} />
 */
export const IconButton = forwardRef<HTMLButtonElement, Props>(function IconButton(
  { icon, label, variant = "default", dot, tooltip = true, className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      data-tooltip={tooltip ? label : undefined}
      className={cx("sa-icon-btn", variant === "outline" && "sa-icon-btn--outline", variant === "primary" && "sa-icon-btn--primary", className)}
      {...rest}
    >
      <Icon name={icon} />
      {dot && <span className="sa-icon-btn__dot" aria-hidden="true" />}
    </button>
  );
});
