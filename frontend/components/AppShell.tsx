"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, logout } from "@/lib/api";
import { useConfirm } from "@/components/ConfirmProvider";
import { useCurrentUser } from "@/components/CurrentUserProvider";
import { MAIN_NAV_GROUPS } from "@/lib/sidebar-configs";
import type { NavGroup } from "@/lib/sidebar-configs";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/Button";
import Sidebar, { isNavActive } from "@/components/Sidebar";
import Header from "@/components/Header";
import type { HeaderStats } from "@/components/Header";
import IdleGuard from "@/components/IdleGuard";

/** Suit l'état réseau du navigateur et le publie sur <html data-net> (bandeaux du design system). */
function useNetwork() {
  const [network, setNetwork] = useState<"online" | "offline">("online");
  useEffect(() => {
    const update = () => {
      const state = navigator.onLine ? "online" : "offline";
      setNetwork(state);
      if (state === "offline") document.documentElement.setAttribute("data-net", "offline");
      else document.documentElement.removeAttribute("data-net");
    };
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
      document.documentElement.removeAttribute("data-net");
    };
  }, []);
  return network;
}

/**
 * Coque de l'application : sidebar 260 px, header 56 px, contenu, barre basse
 * mobile, bandeau hors ligne et bouton flottant du chat. Centralise le filtrage
 * RBAC du menu, les compteurs de dossiers et la déconnexion confirmée.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname() || "";
  const { user, clear } = useCurrentUser();
  const confirm = useConfirm();
  const network = useNetwork();
  const [navOpen, setNavOpen] = useState(false);
  const [stats, setStats] = useState<HeaderStats>(null);

  // ── RBAC : groupes visibles selon les permissions effectives ──
  const permissions: Record<string, Record<string, boolean>> = (user as any)?.permissions || {};
  const groups: NavGroup[] = useMemo(
    () => MAIN_NAV_GROUPS.filter((g) => !g.requiredModule || permissions[g.requiredModule]?.read === true),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user],
  );
  const canValidate = permissions["validation"]?.read === true;

  // ── Compteurs de dossiers (sidebar + cloche), rafraîchis toutes les 60 s ──
  const loadStats = useCallback(async () => {
    if (!canValidate) return;
    try {
      const s = await api.getStats();
      const by = s?.by_status ?? {};
      setStats({ soumis: by.soumis ?? 0, en_validation: by.en_validation ?? 0, complement_requis: by.complement_requis ?? 0 });
    } catch {
      /* compteurs indisponibles : le menu reste utilisable */
    }
  }, [canValidate]);

  useEffect(() => {
    void loadStats();
    const id = setInterval(loadStats, 60_000);
    return () => clearInterval(id);
  }, [loadStats, pathname]);

  // ── Tiroir mobile ──
  const setNav = useCallback((open: boolean) => {
    setNavOpen(open);
    document.documentElement.setAttribute("data-sidebar", open ? "open" : "closed");
  }, []);
  useEffect(() => setNav(false), [pathname, setNav]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setNav(false);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.documentElement.removeAttribute("data-sidebar");
    };
  }, [setNav]);

  async function onLogout() {
    const ok = await confirm({
      title: "Se déconnecter ?",
      message: "Vous allez quitter la session MA2E. Toute donnée non enregistrée sera perdue.",
      confirmText: "Se déconnecter",
      cancelText: "Annuler",
      variant: "danger",
    });
    if (!ok) return;
    await logout();
    clear();
    router.replace("/login");
  }

  // ── Barre basse mobile : 3 premières entrées accessibles + Menu ──
  const quick = groups.flatMap((g) => g.items ?? []).slice(0, 3);

  return (
    <div className="sa-app">
      <a href="#contenu" className="sa-skip-link">
        Aller au contenu
      </a>
      <IdleGuard />
      <Sidebar groups={groups} counts={{ a_traiter: stats ? stats.soumis + stats.en_validation : 0 }} mobileOpen={navOpen} onMobileClose={() => setNav(false)} />
      <div className="sa-scrim" aria-hidden="true" onClick={() => setNav(false)} />

      <div className="sa-app__body">
        <Header
          user={user}
          stats={stats}
          canValidate={canValidate}
          network={network}
          navOpen={navOpen}
          onToggleNav={() => setNav(!navOpen)}
          onRefresh={() => {
            router.refresh();
            void loadStats();
          }}
          onLogout={onLogout}
        />

        <div className="sa-netline" aria-hidden="true">
          <Icon name="wifi-off-01" size={16} />
          <span className="sa-netline__text">Hors ligne</span>
        </div>
        <div className="sa-banner sa-banner--offline" role="region" aria-label="État de la connexion">
          <Icon name="wifi-off-01" />
          <p className="sa-banner__text">
            <b>Connexion perdue.</b> Les données affichées peuvent ne plus être à jour.
          </p>
          <Button size="sm" variant="outline" onClick={() => router.refresh()}>
            Réessayer
          </Button>
        </div>

        <main className="sa-main" id="contenu" tabIndex={-1}>
          {children}
        </main>

        <nav className="sa-bottom-nav" aria-label="Navigation rapide">
          {quick.map((it) => (
            <Link key={it.href} href={it.href} aria-current={isNavActive(pathname, it.href, it.activePrefixes) ? "page" : undefined}>
              <Icon name={it.icon} size={24} />
              <span>{it.label.length > 14 ? `${it.label.slice(0, 13)}…` : it.label}</span>
            </Link>
          ))}
          <a
            href="#sidebar"
            role="button"
            aria-label="Ouvrir le menu complet"
            onClick={(e) => {
              e.preventDefault();
              setNav(true);
            }}
          >
            <Icon name="menu-01" size={24} />
            <span>Menu</span>
          </a>
        </nav>
      </div>

    </div>
  );
}
