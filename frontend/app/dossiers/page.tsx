"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, getUser, STATUS_LABELS } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FloatingChatButton from "@/components/FloatingChatButton";
import {
  IconActivity,
  IconAlertCircle,
  IconArrowRight,
  IconCheck,
  IconChevronDown,
  IconClock,
  IconFileText,
  IconRefresh,
  IconTrendingUp,
  IconX,
} from "@/components/icons";

type Dossier = {
  id: string;
  dossier_number: string;
  status: string;
  matricule: string | null;
  employeur_code: string | null;
  end_user_name?: string | null;
  end_user_contact?: string | null;
  submitted_at: string | null;
  created_at: string;
};

type Stats = { total: number; by_status: Record<string, number> };

const STATUS_FILTERS = [
  { key: "", label: "Tous" },
  { key: "soumis", label: "Soumis" },
  { key: "en_validation", label: "En validation" },
  { key: "valide", label: "Validés" },
  { key: "rejete", label: "Rejetés" },
  { key: "complement_requis", label: "Complément" },
];

const STATUS_PILL: Record<string, string> = {
  en_cours: "bg-ink-100 text-ink-700",
  soumis: "bg-primary-50 text-primary-700",
  en_validation: "bg-accent-50 text-accent-700",
  valide: "bg-primary-100 text-primary-800",
  rejete: "bg-red-50 text-red-700",
  complement_requis: "bg-purple-50 text-purple-700",
};

const STATUS_DOT: Record<string, string> = {
  en_cours: "bg-ink-400",
  soumis: "bg-primary-500",
  en_validation: "bg-accent-500",
  valide: "bg-primary-600",
  rejete: "bg-red-500",
  complement_requis: "bg-purple-500",
};

export default function DossiersPage() {
  const router = useRouter();
  const [user, setU] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>("");
  const [dossiers, setDossiers] = useState<Dossier[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setU(getUser());
    boot();
  }, [router]);

  async function boot() {
    setLoading(true);
    try {
      const tenantList = await api.listTenants();
      setTenants(tenantList);
      const u = getUser();
      const initial =
        u?.role === "super_admin"
          ? tenantList.find((t: any) => t.is_active)?.id ?? tenantList[0]?.id ?? ""
          : u?.tenant_id ?? "";
      setSelectedTenant(initial);
      await load(initial, statusFilter);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function load(tenantId: string, status: string) {
    setLoading(true);
    try {
      const u = getUser();
      const tid = u?.role === "super_admin" ? tenantId : undefined;
      const [d, s] = await Promise.all([
        api.listDossiers(tid, status || undefined),
        api.getStats(tid),
      ]);
      setDossiers(d);
      setStats(s);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onTenantChange(tid: string) {
    setSelectedTenant(tid);
    await load(tid, statusFilter);
  }

  async function onFilterChange(s: string) {
    setStatusFilter(s);
    await load(selectedTenant, s);
  }

  const activeTenant = tenants.find((t) => t.id === selectedTenant);
  const filtered = dossiers.filter((d) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      d.dossier_number.toLowerCase().includes(q) ||
      (d.end_user_name || "").toLowerCase().includes(q) ||
      (d.matricule || "").toLowerCase().includes(q) ||
      (d.end_user_contact || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar tenants={tenants} selectedTenant={selectedTenant} onTenantChange={onTenantChange} />
      <FloatingChatButton />

      <main className="lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-end justify-between mb-8 flex-wrap gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.12em] text-primary-600 font-semibold mb-1.5">
              Console MA2E
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
              Dossiers d'identification
              {activeTenant && (
                <span className="ml-2 text-ink-400 font-light">
                  · {activeTenant.name}
                </span>
              )}
            </h1>
            <p className="text-ink-500 mt-1 text-[15px] font-light">
              Validation et suivi des enrôlements sociétaires
            </p>
          </div>
          <button
            onClick={() => load(selectedTenant, statusFilter)}
            className="inline-flex items-center gap-2 text-sm font-medium text-ink-600 hover:text-ink-900 bg-white hover:bg-ink-50 border border-ink-200 rounded-sm px-3.5 py-2 transition shadow-soft"
          >
            <IconRefresh size={15} />
            Actualiser
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <HeroStatCard
              label="Total des dossiers"
              value={stats.total}
              icon={<IconFileText size={18} />}
              accent="primary"
              hint="Tous statuts confondus"
              spark={[3, 5, 4, 7, 6, 8, stats.total]}
            />
            <StatCard
              label="En attente de validation"
              value={(stats.by_status.soumis ?? 0) + (stats.by_status.en_validation ?? 0)}
              icon={<IconClock size={16} />}
              hint={`${stats.by_status.soumis ?? 0} soumis · ${stats.by_status.en_validation ?? 0} en cours`}
              tone="info"
            />
            <StatCard
              label="Dossiers validés"
              value={stats.by_status.valide ?? 0}
              icon={<IconCheck size={16} />}
              hint="Sociétaires enrôlés"
              tone="success"
            />
            <StatCard
              label="À corriger"
              value={(stats.by_status.rejete ?? 0) + (stats.by_status.complement_requis ?? 0)}
              icon={<IconActivity size={16} />}
              hint={`${stats.by_status.rejete ?? 0} rejetés · ${stats.by_status.complement_requis ?? 0} compléments`}
              tone="warning"
            />
          </div>
        )}

        <div className="bg-white border border-ink-100 rounded-sm overflow-hidden">
          <div className="px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
            <div className="text-[13px] font-medium text-ink-700">
              {filtered.length} dossier{filtered.length > 1 ? "s" : ""}
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Rechercher…"
                  className="w-64 bg-ink-50 hover:bg-white focus:bg-white border border-ink-200 focus:border-primary-500 rounded-sm pl-8 pr-3 py-2 text-[13px] placeholder:text-ink-400 focus:outline-none transition"
                />
                <svg
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-400"
                  width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>

              <div className="relative">
                <select
                  value={statusFilter}
                  onChange={(e) => onFilterChange(e.target.value)}
                  className="appearance-none bg-ink-50 hover:bg-white border border-ink-200 hover:border-ink-300 rounded-sm pl-3 pr-9 py-2 text-[13px] font-medium text-ink-700 cursor-pointer focus:outline-none focus:border-primary-500 transition"
                >
                  {STATUS_FILTERS.map((f) => (
                    <option key={f.key} value={f.key}>
                      {f.key === "" ? "Filtrer par statut : Tous" : `Statut : ${f.label}`}
                    </option>
                  ))}
                </select>
                <IconChevronDown
                  size={14}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-500 pointer-events-none"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="m-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-800 rounded-sm px-3.5 py-2.5 text-sm">
              <IconAlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-[#F9FBFA] text-ink-500 text-[10px] uppercase tracking-[0.1em] font-semibold border-b border-ink-100 divide-x divide-ink-100">
                  <th className="text-left px-5 py-3 font-semibold">Dossier</th>
                  <th className="text-left px-5 py-3 font-semibold">Sociétaire</th>
                  <th className="text-left px-5 py-3 font-semibold">Matricule</th>
                  <th className="text-left px-5 py-3 font-semibold">Employeur</th>
                  <th className="text-left px-5 py-3 font-semibold">Statut</th>
                  <th className="text-left px-5 py-3 font-semibold">Soumis</th>
                  <th className="text-left px-5 py-3 font-semibold w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-16 text-center">
                      <span className="inline-flex gap-1">
                        <span className="w-2 h-2 bg-primary-300 rounded-full animate-bounce" />
                        <span className="w-2 h-2 bg-primary-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-2 h-2 bg-primary-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </span>
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState query={search} hasFilter={!!statusFilter} />
                    </td>
                  </tr>
                ) : (
                  filtered.map((d) => (
                    <tr
                      key={d.id}
                      className="hover:bg-primary-50/40 cursor-pointer transition group divide-x divide-ink-100"
                      onClick={() => router.push(`/dossiers/${d.id}`)}
                    >
                      <td className="px-5 py-4">
                        <div className="font-mono text-primary-700 font-medium text-[13px]">
                          {d.dossier_number}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-9 h-9 rounded-sm bg-primary-100 text-primary-700 flex items-center justify-center text-[13px] font-semibold border border-primary-200/80">
                            {(d.end_user_name || "?").charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="text-ink-900 font-medium leading-tight">
                              {d.end_user_name || "—"}
                            </div>
                            <div className="text-[12px] text-ink-500 leading-tight mt-0.5">
                              {d.end_user_contact}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-ink-700 font-mono text-[13px]">{d.matricule || "—"}</td>
                      <td className="px-5 py-4 text-ink-700 text-[13px]">{d.employeur_code || "—"}</td>
                      <td className="px-5 py-4">
                        <span className={`badge ${STATUS_PILL[d.status] || ""}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[d.status] || ""}`} />
                          {STATUS_LABELS[d.status] || d.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-ink-500 text-[13px]">
                        {d.submitted_at
                          ? new Date(d.submitted_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
                          : "—"}
                      </td>
                      <td className="px-5 py-4 text-ink-300 group-hover:text-primary-600 transition">
                        <IconArrowRight size={16} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        </div>
      </main>
    </div>
  );
}

function HeroStatCard({
  label,
  value,
  icon,
  hint,
  spark,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  accent: "primary";
  hint?: string;
  spark?: number[];
}) {
  return (
    <div className="bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 text-white rounded-sm shadow-card p-5 relative overflow-hidden">
      <div className="absolute -top-12 -right-12 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
      <div className="absolute -bottom-16 -left-8 w-32 h-32 bg-accent-400/15 rounded-full blur-2xl" />

      <div className="relative">
        <div className="flex items-start justify-between mb-3">
          <div className="text-[10px] uppercase tracking-[0.12em] text-white/70 font-semibold">
            {label}
          </div>
          <span className="w-8 h-8 rounded-sm bg-white/15 backdrop-blur flex items-center justify-center">
            {icon}
          </span>
        </div>
        <div className="text-[36px] leading-none font-semibold tracking-tight">
          {value}
        </div>
        {hint && (
          <div className="text-[11px] text-white/70 mt-2 font-light">{hint}</div>
        )}
        {spark && spark.length > 0 && (
          <div className="flex items-end gap-1 mt-4 h-7">
            {spark.map((v, i) => {
              const max = Math.max(...spark, 1);
              const h = Math.max(8, (v / max) * 100);
              return (
                <div
                  key={i}
                  className={`flex-1 rounded-sm ${
                    i === spark.length - 1 ? "bg-accent-400" : "bg-white/30"
                  }`}
                  style={{ height: `${h}%` }}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  tone,
  hint,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: "info" | "warning" | "success" | "danger";
  hint?: string;
}) {
  const config = {
    info: {
      icon: "text-primary-700 bg-primary-50",
      accent: "bg-primary-500",
    },
    warning: {
      icon: "text-accent-700 bg-accent-50",
      accent: "bg-accent-500",
    },
    success: {
      icon: "text-primary-700 bg-primary-100",
      accent: "bg-primary-600",
    },
    danger: {
      icon: "text-red-700 bg-red-50",
      accent: "bg-red-500",
    },
  }[tone];

  return (
    <div className="bg-white border border-ink-200 rounded-sm shadow-soft p-5 hover:border-primary-300 hover:shadow-card transition group relative overflow-hidden">
      <div
        className={`absolute top-0 left-0 right-0 h-0.5 ${config.accent} opacity-0 group-hover:opacity-100 transition`}
      />
      <div className="flex items-start justify-between mb-3">
        <div className="text-[10px] uppercase tracking-[0.12em] text-ink-500 font-semibold">
          {label}
        </div>
        <span className={`w-8 h-8 rounded-sm flex items-center justify-center ${config.icon}`}>
          {icon}
        </span>
      </div>
      <div className="text-[32px] leading-none font-semibold tracking-tight text-ink-900">
        {value}
      </div>
      {hint && (
        <div className="text-[11px] text-ink-500 mt-2 font-light">{hint}</div>
      )}
    </div>
  );
}

function EmptyState({ query, hasFilter }: { query: string; hasFilter: boolean }) {
  return (
    <div className="py-20 text-center">
      <div className="inline-flex w-14 h-14 rounded-sm bg-primary-50 text-primary-500 items-center justify-center mb-4">
        <IconFileText size={26} />
      </div>
      <div className="text-ink-900 font-medium">
        {query ? "Aucun résultat" : hasFilter ? "Aucun dossier dans ce statut" : "Aucun dossier pour le moment"}
      </div>
      <p className="text-sm text-ink-500 mt-1.5 max-w-sm mx-auto font-light leading-relaxed">
        {query
          ? `Aucun dossier ne correspond à « ${query} ».`
          : "Démarrez une conversation avec l'assistant via le chat web ou WhatsApp pour générer le premier dossier."}
      </p>
    </div>
  );
}
