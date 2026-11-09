"use client";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import type { NavGroup } from "@/lib/sidebar-configs";

type NavProps = {
  groups: NavGroup[];
  isActive: (href: string, activePrefixes?: string[]) => boolean;
  /** Clés des groupes ouverts (2 maximum, géré par Sidebar). */
  openGroups: string[];
  onToggleGroup: (key: string) => void;
  onItemClick?: () => void;
  /** Compteurs par type de badge. */
  counts?: { a_traiter?: number };
};

/**
 * Zone de navigation (seule partie qui défile, barre masquée) : groupes
 * repliables en accordéon accessible (`aria-expanded` / `aria-controls`,
 * contenu fermé `inert`), item actif `aria-current="page"`, compteurs.
 */
export default function SidebarNav({ groups, isActive, openGroups, onToggleGroup, onItemClick, counts }: NavProps) {
  return (
    <nav id="nav-zone" aria-label="Menu principal">
      {groups.map((group, gi) => {
        const items = group.items ?? [];
        const isOpen = openGroups.includes(group.key);
        const groupCount = items.reduce((n, it) => n + (it.badge ? (counts?.[it.badge] ?? 0) : 0), 0);

        if (items.length === 0 && group.href) {
          return (
            <ul key={group.key} className="sa-nav" style={{ marginBottom: 4 }}>
              <li>
                <Link href={group.href} onClick={onItemClick} className="sa-nav-item" aria-current={isActive(group.href, group.activePrefixes) ? "page" : undefined}>
                  <Icon name={group.icon ?? "folder-01"} />
                  <span className="sa-nav-item__label">{group.label}</span>
                </Link>
              </li>
            </ul>
          );
        }

        return (
          <div key={group.key} className={`sa-nav-groupe${isOpen ? " is-ouvert" : ""}`} data-titre={group.label}>
            <h2 className="sa-nav-groupe__titre">
              <button
                type="button"
                className="sa-nav-groupe__btn"
                id={`nav-s${gi}`}
                onClick={() => onToggleGroup(group.key)}
                aria-expanded={isOpen}
                aria-controls={`nav-p${gi}`}
              >
                <span className="sa-nav-groupe__lib">{group.label}</span>
                {!isOpen && groupCount > 0 && (
                  <span className="sa-nav-groupe__pastille">
                    <span className="sa-sr-only">{groupCount} à traiter</span>
                    <span aria-hidden="true">{groupCount > 99 ? "99+" : groupCount}</span>
                  </span>
                )}
                <Icon name="arrow-down-01" size={16} />
              </button>
            </h2>
            <div className="sa-nav-groupe__corps" id={`nav-p${gi}`} role="region" aria-labelledby={`nav-s${gi}`} {...(!isOpen ? ({ inert: "" } as Record<string, string>) : {})}>
              <ul className="sa-nav">
                {items.map((item) => {
                  const count = item.badge ? (counts?.[item.badge] ?? 0) : 0;
                  return (
                    <li key={item.href}>
                      <Link href={item.href} onClick={onItemClick} className="sa-nav-item" aria-current={isActive(item.href, item.activePrefixes) ? "page" : undefined}>
                        <Icon name={item.icon} />
                        <span className="sa-nav-item__label">{item.label}</span>
                        {count > 0 && (
                          <span className="sa-nav-item__count sa-nav-item__count--late">
                            <span className="sa-sr-only">{count} à traiter</span>
                            <span aria-hidden="true">{count > 99 ? "99+" : count}</span>
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        );
      })}
    </nav>
  );
}
