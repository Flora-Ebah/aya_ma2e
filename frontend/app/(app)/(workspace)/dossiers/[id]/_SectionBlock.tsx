import type { ReactNode } from "react";
import { TOC } from "./_constants";

/** Section numérotée du dossier (carte) — le numéro suit l'ordre du sommaire. */
export function SectionBlock({
  id, title, subtitle, children,
}: {
  id: string;
  title: string;
  subtitle?: string;
  /** Conservé pour compatibilité ; la signature visuelle est le numéro de section. */
  icon?: ReactNode;
  children: ReactNode;
}) {
  const idx = TOC.findIndex((t) => t.id === id);
  const num = idx >= 0 ? String(idx + 1).padStart(2, "0") : null;
  return (
    <section id={id} className="sa-card" aria-labelledby={`${id}-titre`}>
      <div>
        <h2 className="sa-section-title" style={{ marginBottom: subtitle ? 2 : 0 }}>
          {num && <span className="sa-section-title__num" aria-hidden="true">{num}</span>}
          <span className="sa-section-title__label" id={`${id}-titre`}>{title}</span>
        </h2>
        {subtitle && <p className="sa-help" style={{ margin: 0 }}>{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

export function KVTable({ children }: { children: ReactNode }) {
  return <dl className="sa-kv">{children}</dl>;
}

export function KVRow({
  label, value, mono = false,
}: {
  label: string;
  value: any;
  mono?: boolean;
  small?: boolean;
}) {
  const empty = value === null || value === undefined || value === "";
  return (
    <>
      <dt>{label}</dt>
      <dd className={mono ? "sa-mono" : undefined}>
        {empty ? <span className="sa-text-soft" aria-label="Non renseigné">—</span> : value}
      </dd>
    </>
  );
}
