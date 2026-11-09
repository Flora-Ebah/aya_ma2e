"use client";
import { useId, useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

export type TabItem = { id: string; label: string; icon?: string; count?: number | string; disabled?: boolean };

type Props = {
  tabs: TabItem[];
  /** Onglet actif (contrôlé). */
  value: string;
  onChange: (id: string) => void;
  /** Libellé accessible de la liste d'onglets. */
  label?: string;
  className?: string;
};

/**
 * Onglets accessibles (`role=tablist`, flèches ←/→, Début/Fin).
 * Le panneau associé : `<TabPanel tabId=… active=…>` ou `id="panneau-<id>"`.
 *
 *   <Tabs tabs={[{id:"info",label:"Infos"},{id:"docs",label:"Documents",count:3}]} value={tab} onChange={setTab} />
 */
export function Tabs({ tabs, value, onChange, label = "Sections", className }: Props) {
  const base = useId();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const enabled = tabs.filter((t) => !t.disabled);

  function onKey(e: KeyboardEvent, id: string) {
    const i = enabled.findIndex((t) => t.id === id);
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % enabled.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + enabled.length) % enabled.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = enabled.length - 1;
    if (next < 0) return;
    e.preventDefault();
    const target = enabled[next];
    onChange(target.id);
    refs.current[tabs.findIndex((t) => t.id === target.id)]?.focus();
  }

  return (
    <div className={cx("sa-tabs", className)} role="tablist" aria-label={label}>
      {tabs.map((t, i) => (
        <button
          key={t.id}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="button"
          role="tab"
          id={`tab-${base}-${t.id}`}
          className="sa-tab"
          aria-selected={t.id === value}
          aria-controls={`panneau-${t.id}`}
          tabIndex={t.id === value ? 0 : -1}
          disabled={t.disabled}
          onClick={() => onChange(t.id)}
          onKeyDown={(e) => onKey(e, t.id)}
        >
          {t.icon && <Icon name={t.icon} />}
          {t.label}
          {t.count !== undefined && <span className="sa-tab__count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

/** Panneau d'un onglet : rendu seulement si actif. */
export function TabPanel({ tabId, active, children, className }: { tabId: string; active: boolean; children: ReactNode; className?: string }) {
  if (!active) return null;
  return (
    <div role="tabpanel" id={`panneau-${tabId}`} className={cx("sa-tabpanel", className)} tabIndex={0}>
      {children}
    </div>
  );
}
