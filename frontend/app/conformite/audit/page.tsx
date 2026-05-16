"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, getUser } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FloatingChatButton from "@/components/FloatingChatButton";
import { useToast } from "@/components/ConfirmProvider";
import { IconActivity, IconShield } from "@/components/icons";

type AuditLog = {
  id: string;
  action: string;
  actor_type: string;
  actor_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: any;
  created_at: string;
};

const ACTION_META: Record<string, { label: string; tone: string }> = {
  dossier_created: { label: "Dossier créé", tone: "bg-ink-100 text-ink-700" },
  dossier_submitted: { label: "Dossier soumis", tone: "bg-primary-50 text-primary-700" },
  dossier_validated: { label: "Dossier validé", tone: "bg-primary-100 text-primary-800" },
  dossier_rejected: { label: "Dossier rejeté", tone: "bg-red-50 text-red-700" },
  dossier_complement_requested: { label: "Complément demandé", tone: "bg-purple-50 text-purple-700" },
  piece_uploaded: { label: "Pièce téléversée", tone: "bg-accent-50 text-accent-700" },
  piece_ocr_completed: { label: "OCR effectué", tone: "bg-primary-50 text-primary-700" },
  piece_viewed: { label: "Pièce consultée", tone: "bg-ink-100 text-ink-600" },
  consent_given: { label: "Consentement signé", tone: "bg-primary-100 text-primary-800" },
  consent_refused: { label: "Consentement refusé", tone: "bg-red-50 text-red-700" },
  consent_revoked: { label: "Consentement révoqué", tone: "bg-red-50 text-red-700" },
};

const ACTOR_LABEL: Record<string, string> = {
  user: "Gestionnaire",
  end_user: "Sociétaire",
  system: "Système",
};

export default function AuditPage() {
  const router = useRouter();
  const toast = useToast();
  const [user, setUser] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>("");
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<any>({ total: 0, by_action: {} });
  const [actionFilter, setActionFilter] = useState<string>("");
  const [actorFilter, setActorFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setUser(getUser());
    boot();
  }, [router]);

  async function boot() {
    try {
      const tenantList = await api.listTenants();
      setTenants(tenantList);
      const u = getUser();
      const initial =
        u?.role === "super_admin"
          ? tenantList.find((t: any) => t.is_active)?.id ?? tenantList[0]?.id ?? ""
          : u?.tenant_id ?? "";
      setSelectedTenant(initial);
      await load(initial, "", "");
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  async function load(tenantId: string, action: string, actor: string) {
    setLoading(true);
    try {
      const u = getUser();
      const tid = u?.role === "super_admin" ? tenantId : undefined;
      const [items, st] = await Promise.all([
        api.listAuditLogs(tid, action || undefined, actor || undefined),
        api.auditStats(tid),
      ]);
      setLogs(items);
      setStats(st);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar
        tenants={tenants}
        selectedTenant={selectedTenant}
        onTenantChange={(id) => {
          setSelectedTenant(id);
          load(id, actionFilter, actorFilter);
        }}
      />
      <FloatingChatButton />

      <main className="lg:pl-64">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="mb-6 flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="text-[10.5px] uppercase tracking-[0.14em] text-primary-600 font-semibold mb-1.5">
                Conformité ARTCI
              </div>
              <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
                Journal d'audit
              </h1>
              <p className="text-ink-500 mt-1 text-[14px] font-light">
                Append-only · hash chaîné SHA-256 · conforme art.31 loi 2013-450
              </p>
            </div>
            <div className="flex gap-2 items-center">
              <span className="text-[11px] uppercase tracking-[0.14em] text-ink-500 font-semibold">
                Total
              </span>
              <span className="text-[20px] font-semibold text-ink-900 tabular-nums">
                {stats.total}
              </span>
              <span className="text-[11px] text-ink-400 font-light">événements</span>
            </div>
          </div>

          {/* Filtres */}
          <div className="bg-white border border-ink-100 rounded-sm p-3 mb-4 flex flex-wrap gap-2">
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                load(selectedTenant, e.target.value, actorFilter);
              }}
              className="bg-ink-50 border border-ink-200 rounded-sm px-3 py-1.5 text-[12.5px]"
            >
              <option value="">Toutes les actions</option>
              {Object.keys(ACTION_META).map((k) => (
                <option key={k} value={k}>
                  {ACTION_META[k].label}
                </option>
              ))}
            </select>
            <select
              value={actorFilter}
              onChange={(e) => {
                setActorFilter(e.target.value);
                load(selectedTenant, actionFilter, e.target.value);
              }}
              className="bg-ink-50 border border-ink-200 rounded-sm px-3 py-1.5 text-[12.5px]"
            >
              <option value="">Tous les acteurs</option>
              <option value="user">Gestionnaires</option>
              <option value="end_user">Sociétaires</option>
              <option value="system">Système</option>
            </select>
          </div>

          {/* Stats par action */}
          {Object.keys(stats.by_action || {}).length > 0 && (
            <div className="bg-white border border-ink-100 rounded-sm p-4 mb-4">
              <div className="text-[11px] uppercase tracking-[0.14em] text-ink-500 font-semibold mb-3">
                Répartition par action
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats.by_action).map(([k, v]: any) => {
                  const meta = ACTION_META[k] || { label: k, tone: "bg-ink-100 text-ink-700" };
                  return (
                    <span
                      key={k}
                      className={`text-[12px] font-medium px-2.5 py-1 rounded-sm ${meta.tone}`}
                    >
                      {meta.label} · {v}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Timeline */}
          <div className="bg-white border border-ink-100 rounded-sm overflow-hidden">
            {loading ? (
              <div className="p-12 text-center text-ink-400 text-[13px]">Chargement…</div>
            ) : logs.length === 0 ? (
              <div className="p-12 text-center">
                <IconShield size={28} className="text-ink-300 mx-auto mb-2" />
                <div className="text-ink-700 font-medium text-[14px]">Aucun événement</div>
              </div>
            ) : (
              <div className="divide-y divide-ink-100">
                {logs.map((log) => {
                  const meta = ACTION_META[log.action] || {
                    label: log.action,
                    tone: "bg-ink-100 text-ink-600",
                  };
                  return (
                    <div key={log.id} className="px-5 py-3 flex items-start gap-3">
                      <span
                        className={`w-6 h-6 rounded-sm flex items-center justify-center shrink-0 ${meta.tone}`}
                      >
                        <IconActivity size={11} />
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-ink-900 font-medium text-[13.5px]">
                            {meta.label}
                          </span>
                          <span
                            className={`text-[10px] uppercase tracking-wide font-semibold px-1.5 py-0.5 rounded-sm ${meta.tone}`}
                          >
                            {ACTOR_LABEL[log.actor_type] || log.actor_type}
                          </span>
                        </div>
                        <div className="text-[11.5px] text-ink-500 font-light mt-0.5 font-mono">
                          {log.resource_type && log.resource_id && (
                            <span>
                              {log.resource_type}: {log.resource_id.slice(0, 8)}…
                            </span>
                          )}
                          {Object.keys(log.details || {}).length > 0 && (
                            <span>
                              {" · "}
                              {Object.entries(log.details)
                                .slice(0, 3)
                                .map(([k, v]: any) => `${k}=${String(v).slice(0, 40)}`)
                                .join(" · ")}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-[11.5px] text-ink-500 font-light shrink-0 text-right">
                        {new Date(log.created_at).toLocaleString("fr-FR", {
                          dateStyle: "short",
                          timeStyle: "medium",
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="mt-4 text-[11px] text-ink-400 font-light italic text-center">
            Affichage limité aux 100 derniers événements · Export ARTCI à venir
          </div>
        </div>
      </main>
    </div>
  );
}
