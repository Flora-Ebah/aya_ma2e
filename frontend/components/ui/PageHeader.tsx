import { Fragment } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { ButtonLink } from "./Button";
import { cx } from "./util";

export type Crumb = { label: string; href?: string };

/**
 * Fil d'Ariane. Le dernier élément (sans `href`) porte `aria-current="page"`.
 *   <Breadcrumb items={[{ label: "Dossiers", href: "/dossiers" }, { label: "D-2026-0412" }]} />
 */
export function Breadcrumb({ items }: { items: Crumb[] }) {
  if (!items.length) return null;
  return (
    <nav aria-label="Fil d’Ariane">
      <ol className="sa-breadcrumb">
        {items.map((c, i) => (
          <Fragment key={`${c.label}-${i}`}>
            <li>
              {c.href ? (
                <Link href={c.href}>{c.label}</Link>
              ) : (
                <span aria-current={i === items.length - 1 ? "page" : undefined}>{c.label}</span>
              )}
            </li>
            {i < items.length - 1 && (
              <li aria-hidden="true">
                <Icon name="arrow-right-01" size={12} />
              </li>
            )}
          </Fragment>
        ))}
      </ol>
    </nav>
  );
}

type Props = {
  /** Fil d'Ariane (au-dessus du titre). */
  breadcrumb?: Crumb[];
  /** @deprecated Surtitre historique ; préférer `breadcrumb`. */
  eyebrow?: string;
  title: ReactNode;
  /** Description sous le titre. */
  description?: ReactNode;
  /** Alias historique de `description`. */
  subtitle?: ReactNode;
  /** Zone d'actions à droite : UNE seule action primaire. */
  actions?: ReactNode;
  className?: string;
};

/**
 * En-tête de page : fil d'Ariane + H1 Sora + description + actions.
 *   <PageHeader breadcrumb={[{label:"Administration"},{label:"Utilisateurs"}]} title="Utilisateurs" description="Comptes et rôles." actions={<Button icon="user-add-01">Inviter</Button>} />
 */
export function PageHeader({ breadcrumb, eyebrow, title, description, subtitle, actions, className }: Props) {
  const desc = description ?? subtitle;
  return (
    <>
      {breadcrumb && <Breadcrumb items={breadcrumb} />}
      <div className={cx("sa-page-header", className)}>
        <div className="sa-page-header__text">
          {eyebrow && !breadcrumb && <div className="sa-header__eyebrow">{eyebrow}</div>}
          <h1 className="sa-page-title" id="titre-page">
            {title}
          </h1>
          {desc && <p className="sa-page-desc">{desc}</p>}
        </div>
        {actions && <div className="sa-page-actions">{actions}</div>}
      </div>
    </>
  );
}

/**
 * En-tête d'une page de détail : bouton **Retour** + fil d'Ariane + titre.
 * (Un détail est une page, jamais une modale.)
 *
 *   <DetailHeader backHref="/dossiers" backLabel="Dossiers" breadcrumb={[…]} title={<span className="sa-mono">D-2026-0412</span>} badges={<StatusBadge status="valide" />} actions={…} />
 */
export function DetailHeader({
  backHref,
  backLabel = "Retour",
  onBack,
  breadcrumb,
  title,
  description,
  badges,
  actions,
}: {
  backHref?: string;
  backLabel?: string;
  onBack?: () => void;
  breadcrumb?: Crumb[];
  title: ReactNode;
  description?: ReactNode;
  badges?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        {backHref ? (
          <ButtonLink href={backHref} variant="outline" size="sm" icon="arrow-left-01">
            {backLabel}
          </ButtonLink>
        ) : (
          onBack && (
            <button type="button" className="sa-btn sa-btn--outline sa-btn--sm" onClick={onBack}>
              <Icon name="arrow-left-01" />
              {backLabel}
            </button>
          )
        )}
        {breadcrumb && <Breadcrumb items={breadcrumb} />}
      </div>
      <div className="sa-page-header" style={{ marginBottom: 0 }}>
        <div className="sa-page-header__text">
          <h1 className="sa-page-title" id="titre-page" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            {title}
            {badges}
          </h1>
          {description && <p className="sa-page-desc">{description}</p>}
        </div>
        {actions && <div className="sa-page-actions">{actions}</div>}
      </div>
    </div>
  );
}

/** Titre de section numéroté (« 1 · Identité »). */
export function SectionTitle({ num, children, id }: { num?: number | string; children: ReactNode; id?: string }) {
  return (
    <h2 className="sa-section-title" id={id}>
      {num !== undefined && <span className="sa-section-title__num">{num}</span>}
      <span className="sa-section-title__label">{children}</span>
    </h2>
  );
}
