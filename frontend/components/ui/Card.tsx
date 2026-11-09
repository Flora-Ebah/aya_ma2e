"use client";
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { Button } from "./Button";
import { Drawer } from "./Drawer";
import { cx } from "./util";

type CardProps = {
  /** Titre de la carte (Sora). */
  title?: ReactNode;
  subtitle?: ReactNode;
  /** Actions à droite de l'en-tête. */
  actions?: ReactNode;
  children?: ReactNode;
  /** Retire le padding interne (tableaux pleine largeur) : l'en-tête garde le sien. */
  noPadding?: boolean;
  /** Survol relevé (carte cliquable). */
  interactive?: boolean;
  selected?: boolean;
  /** Pied de carte (liens « Voir tout », actions secondaires), poussé en bas. */
  footer?: ReactNode;
  as?: "div" | "section" | "article";
  className?: string;
  id?: string;
};

/**
 * Carte du design system (`sa-card`, radius 8, bordure 1 px).
 *
 *   <Card title="Dossiers récents" subtitle="30 derniers jours" actions={<Button size="sm" variant="outline">Voir tout</Button>}>…</Card>
 *   <Card noPadding title="Liste">  <DataTable … />  </Card>
 */
export function Card({ title, subtitle, actions, children, noPadding, interactive, selected, footer, as: Tag = "div", className, id }: CardProps) {
  const hasHeader = Boolean(title || subtitle || actions);
  return (
    <Tag id={id} className={cx("sa-card", noPadding && "sa-card--flush", interactive && "sa-card--interactive", selected && "sa-card--selected", className)}>
      {hasHeader && <CardHeader title={title} subtitle={subtitle} actions={actions} />}
      {children}
      {footer && <div className="sa-card__footer">{footer}</div>}
    </Tag>
  );
}

/** En-tête de carte : titre + sous-titre à gauche, actions à droite. */
export function CardHeader({ title, subtitle, actions, className }: { title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <div className={cx("sa-card__header", className)}>
      <div>
        {title && <h2 className="sa-card__title">{title}</h2>}
        {subtitle && <div className="sa-card__subtitle">{subtitle}</div>}
      </div>
      {actions && <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>{actions}</div>}
    </div>
  );
}

type ExpandableCardProps = Omit<CardProps, "children"> & {
  children: ReactNode;
  /** Hauteur max du contenu replié (px). Défaut 240. */
  maxHeight?: number;
  /** Libellé du bouton. Défaut « Afficher plus ». */
  moreLabel?: string;
  /** Titre du tiroir plein écran (défaut : titre de la carte). */
  drawerTitle?: string;
  /** Contenu du tiroir (défaut : `children`). */
  drawerContent?: ReactNode;
  /** `drawer` (défaut) ouvre un tiroir plein écran ; `inline` déplie en place. */
  mode?: "drawer" | "inline";
  drawerActions?: ReactNode;
};

/**
 * Carte à contenu extensible : le contenu est tronqué à `maxHeight` ; si ça
 * dépasse, un bouton « Afficher plus » ouvre un **tiroir plein écran** (jamais
 * une modale) avec le contenu complet.
 */
export function ExpandableCard({
  children,
  maxHeight = 240,
  moreLabel = "Afficher plus",
  drawerTitle,
  drawerContent,
  mode = "drawer",
  drawerActions,
  ...card
}: ExpandableCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [overflow, setOverflow] = useState(false);
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const bodyId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setOverflow(el.scrollHeight > maxHeight + 8);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [maxHeight, children]);

  const truncated = overflow && !expanded;
  const title = typeof card.title === "string" ? card.title : undefined;
  return (
    <Card {...card}>
      <div className="sa-extensible">
        <div
          ref={ref}
          id={bodyId}
          className={cx("sa-extensible__corps", truncated && "is-tronque")}
          style={{ ["--ext-h" as string]: `${maxHeight}px` }}
        >
          {children}
        </div>
        {(overflow || expanded) && (
          <div className="sa-extensible__pied">
            <Button
              variant="ghost"
              size="sm"
              icon={mode === "inline" && expanded ? "arrow-up-01" : "arrow-down-01"}
              aria-controls={bodyId}
              aria-expanded={mode === "inline" ? expanded : open}
              onClick={() => (mode === "inline" ? setExpanded((v) => !v) : setOpen(true))}
            >
              {mode === "inline" && expanded ? "Afficher moins" : moreLabel}
            </Button>
          </div>
        )}
      </div>
      {mode === "drawer" && (
        <Drawer open={open} onClose={() => setOpen(false)} title={drawerTitle ?? title ?? "Détail complet"} actions={drawerActions}>
          {drawerContent ?? children}
        </Drawer>
      )}
    </Card>
  );
}

/**
 * Liste clé / valeur (`dl.sa-kv`) pour les fiches détail.
 *   <KeyValueList items={[{ label: "Matricule", value: <span className="sa-mono">A123</span> }]} />
 */
export function KeyValueList({ items, stacked, className }: { items: Array<{ label: ReactNode; value: ReactNode; icon?: string }>; stacked?: boolean; className?: string }) {
  return (
    <dl className={cx("sa-kv", stacked && "sa-kv--stacked", className)}>
      {items.map((it, i) => (
        <KvRow key={i} {...it} />
      ))}
    </dl>
  );
}

function KvRow({ label, value, icon }: { label: ReactNode; value: ReactNode; icon?: string }) {
  return (
    <>
      <dt>
        {icon && <Icon name={icon} size={14} />} {label}
      </dt>
      <dd>{value}</dd>
    </>
  );
}
