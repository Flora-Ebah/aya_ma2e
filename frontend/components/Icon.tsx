import type { SVGProps } from "react";

/**
 * Icône HugeIcons (Stroke 1.5) — référence un symbole du sprite
 * `public/design/icons.svg` injecté une fois dans le body (IconSprite).
 *
 *   <Icon name="home-01" />                      // 20 px par défaut (.i)
 *   <Icon name="alert-02" size={16} />           // taille en px
 *   <Icon name="user" className="h-6 w-6" />     // ou classes Tailwind
 *   <Icon name="tick-02" label="Validé" />       // label accessible (sinon aria-hidden)
 *
 * Le trait suit `currentColor`. Liste des noms : docs/design-kit.md.
 */
export type IconProps = {
  /** Nom HugeIcons sans préfixe `i-` (ex. "home-01"). */
  name: string;
  /** Taille en pixels (sinon 20 px via la classe `.i`). */
  size?: number;
  className?: string;
  /** Libellé accessible (sinon l'icône est décorative : aria-hidden). */
  label?: string;
} & Omit<SVGProps<SVGSVGElement>, "children" | "name">;

export function Icon({ name, size, className = "", label, style, ...rest }: IconProps) {
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true as const };
  return (
    <svg
      className={`i ${className}`.trim()}
      fill="none"
      focusable="false"
      style={size ? { width: size, height: size, ...style } : style}
      {...a11y}
      {...rest}
    >
      <use href={`#i-${name}`} />
    </svg>
  );
}

export default Icon;
