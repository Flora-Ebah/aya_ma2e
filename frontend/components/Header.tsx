"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, logout } from "@/lib/api";
import Logo from "@/components/Logo";
import { IconChevronDown, IconLogOut, IconMessage } from "@/components/icons";

export default function Header({
  tenants,
  selectedTenant,
  onTenantChange,
}: {
  tenants?: any[];
  selectedTenant?: string;
  onTenantChange?: (id: string) => void;
}) {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  function onLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="bg-white border-b border-ink-200 sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/dossiers" className="flex items-center gap-3 group">
            <Logo size={36} />
            <div className="leading-tight">
              <div className="font-semibold text-ink-900 text-[15px]">MA2E</div>
              <div className="text-[11px] text-ink-500 uppercase tracking-wider font-medium">
                Console d'identification
              </div>
            </div>
          </Link>

          {user?.role === "super_admin" && tenants && tenants.length > 0 && onTenantChange && (
            <div className="relative">
              <select
                value={selectedTenant}
                onChange={(e) => onTenantChange(e.target.value)}
                className="appearance-none bg-ink-50 hover:bg-ink-100 border border-ink-200 rounded-sm pl-3 pr-9 py-1.5 text-sm font-medium text-ink-700 transition cursor-pointer"
              >
                {tenants.map((t: any) => (
                  <option key={t.id} value={t.id} disabled={!t.is_active}>
                    {t.name} {!t.is_active ? "· en attente" : ""}
                  </option>
                ))}
              </select>
              <IconChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-500 pointer-events-none" />
            </div>
          )}
        </div>

        <nav className="flex items-center gap-2">
          <Link
            href="/chat"
            target="_blank"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary-700 hover:text-primary-800 bg-primary-50 hover:bg-primary-100 border border-primary-200 rounded-sm px-3.5 py-2 transition"
          >
            <IconMessage size={16} />
            Ouvrir le chat
          </Link>

          <div className="w-px h-6 bg-ink-200 mx-1" />

          <div className="flex items-center gap-3">
            <div className="text-right leading-tight">
              <div className="text-sm font-medium text-ink-900">{user?.name}</div>
              <div className="text-[11px] text-ink-500 uppercase tracking-wider">
                {user?.role?.replace("_", " ")}
              </div>
            </div>
            <div className="w-9 h-9 rounded-sm bg-primary-600 text-white flex items-center justify-center text-sm font-semibold shadow-sm">
              {(user?.name || "U").charAt(0).toUpperCase()}
            </div>
            <button
              onClick={onLogout}
              className="p-2 text-ink-400 hover:text-ink-700 hover:bg-ink-100 rounded-sm transition"
              title="Déconnexion"
            >
              <IconLogOut size={18} />
            </button>
          </div>
        </nav>
      </div>
    </header>
  );
}
