import { cx } from "./util";

type Props = {
  /** Nom complet : sert aux initiales et au libellé accessible. */
  name: string;
  size?: 24 | 32 | 40 | 48;
  /** Fond doux au lieu du fond plein. */
  soft?: boolean;
  /** Pastille de présence. */
  status?: boolean;
  className?: string;
};

export function initials(name: string): string {
  const parts = name.replace(/[@._-]+/g, " ").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Avatar à initiales. */
export function Avatar({ name, size = 32, soft, status, className }: Props) {
  return (
    <span className={cx("sa-avatar", size !== 32 && `sa-avatar--${size}`, soft && "sa-avatar--soft", className)} role="img" aria-label={name}>
      <span aria-hidden="true">{initials(name)}</span>
      {status && <span className="sa-avatar__status" aria-hidden="true" />}
    </span>
  );
}
