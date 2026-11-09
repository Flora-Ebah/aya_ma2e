"use client";
import { useId, useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

export type AccordionItem = {
  id: string;
  title: ReactNode;
  /** Résumé à droite du titre (compteurs, badge). */
  summary?: ReactNode;
  /** Boutons placés hors du bouton d'en-tête. */
  actions?: ReactNode;
  content: ReactNode;
  defaultOpen?: boolean;
};

type Props = {
  items: AccordionItem[];
  /** `true` : un seul panneau ouvert à la fois. */
  single?: boolean;
  className?: string;
};

/**
 * Accordéon accessible (bouton `aria-expanded` / `aria-controls`, région labellisée).
 *   <Accordion items={[{ id:"a", title:"Direction régionale Sud", summary:<Badge>3</Badge>, content:<…/> }]} />
 */
export function Accordion({ items, single, className }: Props) {
  const base = useId();
  const [open, setOpen] = useState<Set<string>>(() => new Set(items.filter((i) => i.defaultOpen).map((i) => i.id)));

  function toggle(id: string) {
    setOpen((prev) => {
      const next = new Set(single ? [] : prev);
      if (prev.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className={cx("sa-acc", className)}>
      {items.map((it) => {
        const isOpen = open.has(it.id);
        const k = `${base}-${it.id}`;
        return (
          <div key={it.id} className={cx("sa-acc__item", isOpen && "is-ouvert")}>
            <div className="sa-acc__entete">
              <button type="button" className="sa-acc__btn" id={`${k}-b`} aria-expanded={isOpen} aria-controls={`${k}-c`} onClick={() => toggle(it.id)}>
                <Icon name="arrow-down-01" size={16} />
                <span className="sa-acc__titre">{it.title}</span>
                {it.summary && <span className="sa-acc__resume">{it.summary}</span>}
              </button>
              {it.actions && <div className="sa-acc__actions">{it.actions}</div>}
            </div>
            <div className="sa-acc__corps" id={`${k}-c`} role="region" aria-labelledby={`${k}-b`} hidden={!isOpen}>
              {isOpen && it.content}
            </div>
          </div>
        );
      })}
    </div>
  );
}
