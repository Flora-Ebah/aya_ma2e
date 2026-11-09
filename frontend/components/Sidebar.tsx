"use client";
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import type { NavGroup } from "@/lib/sidebar-configs";
import FloatingChatButton from "@/components/FloatingChatButton";
import SidebarBrand from "@/components/sidebar/SidebarBrand";
import SidebarNav from "@/components/sidebar/SidebarNav";

const MAX_OPEN = 2;
const STORAGE_KEY = "ma2e-menu";

type Props = {
  /** Groupes déjà filtrés par le RBAC (voir AppShell). */
  groups: NavGroup[];
  counts?: { a_traiter?: number };
  /** Tiroir mobile ouvert. */
  mobileOpen: boolean;
  onMobileClose: () => void;
};

export function isNavActive(pathname: string, href: string, activePrefixes?: string[]) {
  if (pathname === href || pathname.startsWith(href + "/")) return true;
  return !!activePrefixes?.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

/**
 * Sidebar principale (260 px) : en-tête et pied FIXES, seule la zone de
 * navigation défile (barre masquée). Groupes repliables, 2 ouverts au maximum
 * (le plus ancien se referme), le groupe de la page active est toujours ouvert.
 * Le filtrage RBAC est fait en amont (AppShell) ; la configuration est
 * déclarative dans lib/sidebar-configs.ts.
 */
export default function Sidebar({ groups, counts, mobileOpen, onMobileClose }: Props) {
  const pathname = usePathname() || "";
  const [open, setOpen] = useState<string[]>([]);

  const activeKey = groups.find((g) => (g.items ?? []).some((it) => isNavActive(pathname, it.href, it.activePrefixes)))?.key;

  // Initialisation : état mémorisé, sinon groupe actif + premier groupe.
  useEffect(() => {
    let saved: string[] | null = null;
    try {
      const v = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (Array.isArray(v)) saved = v.filter((k) => typeof k === "string");
    } catch {
      /* préférence non lue */
    }
    const keys = groups.map((g) => g.key);
    let init = (saved ?? []).filter((k) => keys.includes(k));
    if (init.length === 0) {
      if (activeKey) init.push(activeKey);
      for (const k of keys) {
        if (init.length >= MAX_OPEN) break;
        if (!init.includes(k)) init.push(k);
      }
    }
    if (activeKey && !init.includes(activeKey)) init = [...init, activeKey].slice(-MAX_OPEN);
    setOpen(init);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups.map((g) => g.key).join("|")]);

  // La page active est toujours visible.
  useEffect(() => {
    if (!activeKey) return;
    setOpen((prev) => (prev.includes(activeKey) ? prev : [...prev, activeKey].slice(-MAX_OPEN)));
  }, [activeKey]);

  const persist = (list: string[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch {
      /* préférence non mémorisée */
    }
  };

  const toggle = useCallback((key: string) => {
    setOpen((prev) => {
      const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key].slice(-MAX_OPEN);
      persist(next);
      return next;
    });
  }, []);

  return (
    <aside id="sidebar" className="sa-sidebar" aria-label="Navigation principale" data-open={mobileOpen || undefined}>
      <SidebarBrand onNavigate={onMobileClose} onClose={onMobileClose} />
      <SidebarNav
        groups={groups}
        isActive={(href, pre) => isNavActive(pathname, href, pre)}
        openGroups={open}
        onToggleGroup={toggle}
        onItemClick={onMobileClose}
        counts={counts}
      />
      <div className="sa-sidebar__footer">
        <FloatingChatButton onNavigate={onMobileClose} />
        <div className="sa-sidebar__signature">
          <span>
            Mutuelle des agents de l&apos;eau et de l&apos;électricité · <b>GS2E</b>
          </span>
        </div>
      </div>
    </aside>
  );
}
