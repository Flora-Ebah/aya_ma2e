"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { Popover } from "@/components/ui/Popover";
import { IconButton } from "@/components/ui/IconButton";
import ThemeToggle from "@/components/ThemeToggle";
import type { CurrentUser } from "@/components/CurrentUserProvider";

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super administrateur",
  tenant_admin: "Administrateur",
  agent: "Gestionnaire",
  viewer: "Lecteur",
};

export type HeaderStats = { soumis: number; en_validation: number; complement_requis: number } | null;

type Props = {
  user: CurrentUser | null;
  stats: HeaderStats;
  /** Accès au module dossiers (cloche d'activité). */
  canValidate: boolean;
  network: "online" | "offline";
  navOpen: boolean;
  onToggleNav: () => void;
  onRefresh: () => void;
  onLogout: () => void;
};

/**
 * En-tête 56 px : menu (tablette/mobile), contexte, recherche globale
 * (Ctrl+K), état réseau, notifications compactes (activité des dossiers) et
 * menu utilisateur (profil, paramètres, thème clair/sombre/système,
 * déconnexion).
 */
export default function Header({ user, stats, canValidate, network, navOpen, onToggleNav, onRefresh, onLogout }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => inputRef.current?.focus(), 0);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    const term = q.trim();
    if (!term) return;
    router.push(`/dossiers?q=${encodeURIComponent(term)}`);
    setSearchOpen(false);
  }

  const name = user?.name || "Utilisateur";
  const roleLabel = user?.role ? (ROLE_LABEL[user.role] ?? user.role.replace("_", " ")) : "";
  const pending = stats ? stats.soumis + stats.en_validation + stats.complement_requis : 0;

  const notifs = stats
    ? [
        { n: stats.soumis, icon: "task-01", text: "dossier(s) soumis en attente de prise en charge" },
        { n: stats.en_validation, icon: "hourglass", text: "dossier(s) en cours de validation" },
        { n: stats.complement_requis, icon: "alert-circle", text: "dossier(s) en attente d'un complément" },
      ].filter((x) => x.n > 0)
    : [];

  return (
    <header className={`sa-header${searchOpen ? " pf-recherche-ouverte" : ""}`}>
      <button className="sa-icon-btn sa-header__menu" type="button" aria-controls="sidebar" aria-expanded={navOpen} aria-label="Ouvrir le menu" onClick={onToggleNav}>
        <Icon name="menu-01" size={24} />
      </button>

      <div className="sa-header__context">
        <span className="sa-header__eyebrow">MA2E · Mutuelle des agents</span>
        <span className="sa-header__entity">Console d&apos;identification</span>
      </div>

      <form className="sa-header__search" role="search" onSubmit={submitSearch}>
        <label className="sa-sr-only" htmlFor="recherche-globale">
          Rechercher un dossier
        </label>
        <div className="sa-input-group">
          <Icon name="search-01" />
          <input
            ref={inputRef}
            id="recherche-globale"
            className="sa-input"
            type="search"
            autoComplete="off"
            placeholder="Matricule, nom, n° de dossier…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
            onKeyDown={(e) => e.key === "Escape" && setSearchOpen(false)}
          />
          <span className="sa-kbd-group" aria-hidden="true">
            <span className="sa-kbd">Ctrl</span>
            <span className="sa-kbd">K</span>
          </span>
        </div>
      </form>
      <IconButton
        icon="search-01"
        label="Rechercher"
        tooltip={false}
        className="sa-header__search-btn"
        onClick={() => {
          setSearchOpen(true);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      />

      <div className="sa-header__actions">
        <button
          type="button"
          className="sa-net"
          data-state={network}
          role="status"
          aria-live="polite"
          title="Actualiser les données"
          onClick={onRefresh}
        >
          <span className="sa-net__dot" />
          <span className="sa-net__state">{network === "online" ? "En ligne" : "Hors ligne"}</span>
          <span className="sa-net__meta">{network === "online" ? " · à jour" : " · connexion perdue"}</span>
        </button>

        {canValidate && (
          <Popover
            role="dialog"
            label="Notifications"
            width={360}
            trigger={({ open: _o, ...p }) => (
              <button type="button" className="sa-icon-btn" aria-label={pending ? `Notifications (${pending} à suivre)` : "Notifications"} {...p}>
                <Icon name="notification-02" />
                {pending > 0 && <span className="sa-icon-btn__dot" aria-hidden="true" />}
              </button>
            )}
          >
            {({ close }) => (
              <>
                <div className="sa-menu__head">
                  <span className="sa-h5">Activité des dossiers</span>
                </div>
                {notifs.length === 0 ? (
                  <div className="sa-body-sm" style={{ padding: 16 }}>
                    Rien à traiter pour le moment.
                  </div>
                ) : (
                  notifs.slice(0, 5).map((n) => (
                    <Link key={n.text} href="/dossiers" className="sa-menu__item" onClick={close} style={{ minHeight: 52 }}>
                      <Icon name={n.icon} />
                      <span>
                        <span className="sa-strong">{n.n}</span> {n.text}
                      </span>
                    </Link>
                  ))
                )}
                <div className="sa-menu__sep" />
                <Link href="/dossiers" className="sa-menu__item" onClick={close}>
                  <Icon name="folder-01" />
                  Voir tous les dossiers
                </Link>
              </>
            )}
          </Popover>
        )}

        <Popover
          role="dialog"
          label="Menu du compte"
          width={300}
          trigger={({ open, ...p }) => (
            <button type="button" className="sa-user-btn" aria-label={`Menu du compte : ${name}`} {...p} aria-expanded={open}>
              <Avatar name={name} status />
              <span className="sa-user-btn__text">
                <span className="sa-user-btn__name">{name}</span>
                <span className="sa-user-btn__role">{roleLabel}</span>
              </span>
              <Icon name="arrow-down-01" size={16} />
            </button>
          )}
        >
          {({ close }) => (
            <>
              <div className="sa-menu__head">
                <div className="sa-micro sa-text-soft" style={{ textTransform: "none", letterSpacing: 0 }}>{user?.email}</div>
                <div className="sa-strong">{name}</div>
                <div className="sa-body-sm sa-text-soft">{roleLabel}</div>
              </div>
              <Link href="/parametres/profil" className="sa-menu__item" onClick={close}>
                <Icon name="user-circle" />
                Mon profil
              </Link>
              <Link href="/parametres/general" className="sa-menu__item" onClick={close}>
                <Icon name="settings-02" />
                Paramètres
              </Link>
              <a href="/chat" target="_blank" rel="noopener" className="sa-menu__item" onClick={close}>
                <Icon name="message-01" />
                Ouvrir le chat public
              </a>
              <div className="sa-menu__theme">
                <span className="sa-body-sm sa-text-soft">Thème</span>
                <ThemeToggle />
              </div>
              <div className="sa-menu__sep" />
              <button
                type="button"
                className="sa-menu__item sa-menu__item--danger"
                onClick={() => {
                  close();
                  onLogout();
                }}
              >
                <Icon name="logout-02" />
                Se déconnecter
              </button>
            </>
          )}
        </Popover>
      </div>
    </header>
  );
}
