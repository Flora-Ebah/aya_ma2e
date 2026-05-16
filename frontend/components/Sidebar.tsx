"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getUser, logout } from "@/lib/api";
import Logo from "@/components/Logo";
import {
  IconActivity,
  IconBuilding,
  IconChevronDown,
  IconFileText,
  IconLogOut,
  IconMessage,
  IconQrCode,
  IconUser,
} from "@/components/icons";

type NavItem = {
  href: string;
  label: string;
  icon: typeof IconFileText;
};

const WORKSPACE_NAV: NavItem[] = [
  { href: "/dossiers", label: "Dossiers", icon: IconFileText },
  { href: "/qr-code", label: "Accès QR", icon: IconQrCode },
];

const SETTINGS_NAV: NavItem[] = [
  { href: "/parametres/knowledge", label: "Base de connaissances", icon: IconMessage },
  { href: "/parametres/employeurs", label: "Employeurs", icon: IconBuilding },
  { href: "/parametres/utilisateurs", label: "Utilisateurs", icon: IconUser },
];

const COMPLIANCE_NAV: NavItem[] = [
  { href: "/conformite/audit", label: "Journal d'audit", icon: IconActivity },
  { href: "/conformite/conversations", label: "Conversations", icon: IconMessage },
];

export default function Sidebar({
  tenants,
  selectedTenant,
  onTenantChange,
}: {
  tenants?: any[];
  selectedTenant?: string;
  onTenantChange?: (id: string) => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setUser(getUser());
  }, []);

  function onLogout() {
    logout();
    router.replace("/login");
  }

  function isActive(href: string) {
    return pathname === href || pathname?.startsWith(href + "/");
  }

  const activeTenantName =
    tenants?.find((t: any) => t.id === selectedTenant)?.name || "—";
  const initial = (user?.name || "·").trim().charAt(0).toUpperCase();

  return (
    <>
      <div className="lg:hidden bg-white border-b border-ink-100 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
        <Link href="/dossiers" className="flex items-center gap-2">
          <Logo size={28} />
          <span className="font-semibold text-ink-900 text-[15px]">MA2E</span>
        </Link>
        <button
          onClick={() => setMobileOpen(true)}
          className="p-2 text-ink-500 hover:text-ink-900"
          aria-label="Menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>

      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-ink-900/40 backdrop-blur-sm z-40 animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 w-64 bg-white border-r border-ink-100 flex flex-col z-40 font-sidebar transform transition-transform lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="px-4 pt-5 pb-4">
          <Link
            href="/dossiers"
            className="inline-flex items-center gap-2.5"
            onClick={() => setMobileOpen(false)}
          >
            <Logo size={36} />
            <div className="flex flex-col leading-none">
              <span className="text-[15px] font-semibold tracking-tight text-ink-900">
                MA<span className="text-primary-500">2</span>E
              </span>
              <span className="text-[10.5px] text-ink-400 mt-1 font-normal">
                Identification digitale
              </span>
            </div>
          </Link>
        </div>

        {user?.role === "super_admin" && tenants && tenants.length > 0 && onTenantChange && (
          <div className="mx-3 mb-3">
            <div className="relative bg-ink-50 hover:bg-ink-100 rounded-sm border border-ink-200 transition group">
              <div className="flex items-center gap-2.5 px-2.5 py-2">
                <div className="w-6 h-6 rounded-sm bg-primary-100 flex items-center justify-center shrink-0">
                  <IconBuilding size={11} className="text-primary-700" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[9.5px] uppercase tracking-[0.14em] text-ink-400 font-medium leading-none">
                    Tenant
                  </div>
                  <div className="text-[12.5px] font-medium text-ink-900 leading-none mt-1 truncate">
                    {activeTenantName}
                  </div>
                </div>
                <IconChevronDown size={13} className="text-ink-400 shrink-0" />
              </div>
              <select
                value={selectedTenant}
                onChange={(e) => onTenantChange(e.target.value)}
                className="absolute inset-0 opacity-0 cursor-pointer"
              >
                {tenants.map((t: any) => (
                  <option key={t.id} value={t.id} disabled={!t.is_active}>
                    {t.name} {!t.is_active ? "· en attente" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <nav className="flex-1 px-3 pt-4 overflow-y-auto">
          <NavSection
            label="Espace de travail"
            items={WORKSPACE_NAV}
            isActive={isActive}
            onClick={() => setMobileOpen(false)}
          />

          <div className="my-4 h-px bg-ink-100" />

          <NavSection
            label="Paramètres"
            items={SETTINGS_NAV}
            isActive={isActive}
            onClick={() => setMobileOpen(false)}
          />

          <div className="my-4 h-px bg-ink-100" />

          <NavSection
            label="Conformité ARTCI"
            items={COMPLIANCE_NAV}
            isActive={isActive}
            onClick={() => setMobileOpen(false)}
          />
        </nav>

        <div className="border-t border-ink-100 px-3 py-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-sm bg-primary-600 text-white flex items-center justify-center text-[12px] font-semibold shrink-0">
              {initial}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-medium text-ink-900 truncate leading-none">
                {user?.name || "—"}
              </div>
              <div className="text-[10.5px] text-ink-500 truncate mt-1 capitalize">
                {user?.role?.replace("_", " ") || ""}
              </div>
            </div>
            <button
              onClick={onLogout}
              className="w-7 h-7 flex items-center justify-center text-ink-400 hover:text-red-600 hover:bg-red-50 rounded-sm transition"
              title="Déconnexion"
              aria-label="Déconnexion"
            >
              <IconLogOut size={14} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-2.5 pt-1 pb-2 text-[9.5px] uppercase tracking-[0.16em] text-ink-400 font-semibold">
      {children}
    </div>
  );
}

function NavSection({
  label,
  items,
  isActive,
  onClick,
}: {
  label: string;
  items: NavItem[];
  isActive: (href: string) => boolean;
  onClick: () => void;
}) {
  return (
    <section>
      <SectionLabel>{label}</SectionLabel>
      <div className="space-y-0.5">
        {items.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClick}
              className={`group relative flex items-center gap-2.5 px-2.5 py-1.5 rounded-sm transition ${
                active
                  ? "text-accent-700"
                  : "text-ink-600 hover:bg-ink-50 hover:text-ink-900"
              }`}
            >
              {active && (
                <>
                  {/* Trait vertical à gauche */}
                  <span
                    aria-hidden
                    className="absolute left-0 top-1 bottom-1 w-[3px] bg-accent-500 rounded-r-full"
                  />
                  {/* Tail fade gauche → droite */}
                  <span
                    aria-hidden
                    className="absolute inset-0 rounded-sm bg-gradient-to-r from-accent-500/15 via-accent-500/5 to-transparent pointer-events-none"
                  />
                </>
              )}
              <Icon
                size={15}
                className={`relative ${
                  active
                    ? "text-accent-600"
                    : "text-ink-400 group-hover:text-ink-600 transition"
                }`}
              />
              <span
                className={`relative text-[13px] tracking-tight ${
                  active ? "font-semibold" : "font-medium"
                }`}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
