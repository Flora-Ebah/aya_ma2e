import { forwardRef } from "react";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import Link from "next/link";
import { cx, renderIcon } from "./util";
import type { IconProp } from "./util";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
export type ButtonSize = "sm" | "md" | "lg";

type CommonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Nom d'icône du sprite ("plus-sign") ou élément React. */
  icon?: IconProp;
  iconRight?: IconProp;
  /** Affiche un spinner et désactive le bouton. */
  loading?: boolean;
  /** Occupe toute la largeur du conteneur. */
  block?: boolean;
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & CommonProps;

const VARIANT: Record<ButtonVariant, string> = {
  primary: "sa-btn--primary",
  secondary: "sa-btn--secondary",
  ghost: "sa-btn--ghost",
  danger: "sa-btn--danger",
  outline: "sa-btn--outline",
};
const SIZE: Record<ButtonSize, string> = { sm: "sa-btn--sm", md: "", lg: "sa-btn--lg" };

export function buttonClass({ variant = "primary", size = "md", block, className }: CommonProps & { className?: string }) {
  return cx("sa-btn", VARIANT[variant], SIZE[size], block && "sa-btn--block", className);
}

/**
 * Bouton du design system (44 px, MAJUSCULES via le CSS, focus ring visible).
 * Une seule action `primary` par zone.
 *
 *   <Button icon="plus-sign" onClick={…}>Nouveau dossier</Button>
 *   <Button variant="danger" size="sm" loading={busy}>Supprimer</Button>
 */
export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", size = "md", icon, iconRight, loading = false, block, disabled, className, children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={buttonClass({ variant, size, block, className })}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className="sa-spinner sa-spinner--sm" aria-hidden="true" /> : renderIcon(icon)}
      {children}
      {!loading && renderIcon(iconRight)}
    </button>
  );
});

type LinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & CommonProps & { href: string; children?: ReactNode };

/** Lien (next/link) habillé comme un bouton. */
export function ButtonLink({ variant = "primary", size = "md", icon, iconRight, block, className, children, href, ...rest }: LinkProps) {
  return (
    <Link href={href} className={buttonClass({ variant, size, block, className })} {...rest}>
      {renderIcon(icon)}
      {children}
      {renderIcon(iconRight)}
    </Link>
  );
}
