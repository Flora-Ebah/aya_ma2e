"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, getUser } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FloatingChatButton from "@/components/FloatingChatButton";
import { useConfirm, useToast } from "@/components/ConfirmProvider";
import {
  IconActivity,
  IconAlertCircle,
  IconCheck,
  IconRefresh,
  IconX,
} from "@/components/icons";

type Source = {
  id: string;
  type: string;
  source_url: string;
  title: string | null;
  chunks_count: number;
  status: string;
  last_crawled_at: string | null;
};

type LogEntry = {
  stage: string;
  ts: string;
  message: string;
  level: "info" | "success" | "error";
};

const STATUS_COLOR: Record<string, string> = {
  ready: "bg-primary-50 text-primary-700 border-primary-200",
  ingesting: "bg-accent-50 text-accent-700 border-accent-200",
  empty: "bg-ink-100 text-ink-700 border-ink-200",
  pending: "bg-purple-50 text-purple-700 border-purple-200",
};

export default function KnowledgePage() {
  const router = useRouter();
  const confirm = useConfirm();
  const toast = useToast();

  const [user, setUser] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>("");
  const [sources, setSources] = useState<Source[]>([]);
  const [stats, setStats] = useState<{ sources: number; chunks: number }>({
    sources: 0,
    chunks: 0,
  });
  const [loading, setLoading] = useState(true);

  // Ingestion form
  const [url, setUrl] = useState("https://www.ma2e.ci/");
  const [maxPages, setMaxPages] = useState(30);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const logRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setUser(getUser());
    boot();
  }, [router]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  useEffect(() => {
    return () => {
      if (esRef.current) esRef.current.close();
    };
  }, []);

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
      await load(initial);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  async function load(tenantId: string) {
    try {
      const u = getUser();
      const tid = u?.role === "super_admin" ? tenantId : undefined;
      const [srcs, st] = await Promise.all([
        api.listKnowledgeSources(tid),
        api.knowledgeStats(tid),
      ]);
      setSources(srcs);
      setStats(st);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  function pushLog(stage: string, message: string, level: LogEntry["level"] = "info") {
    setLogs((prev) => [
      ...prev,
      {
        stage,
        ts: new Date().toLocaleTimeString("fr-FR"),
        message,
        level,
      },
    ]);
  }

  function startIngestion() {
    if (running) return;
    if (!url.trim()) {
      toast({ tone: "error", title: "URL requise" });
      return;
    }

    setRunning(true);
    setLogs([]);
    setProgress({ current: 0, total: 0 });
    pushLog("init", `Démarrage du scraping de ${url}`, "info");

    const u = getUser();
    const tid = u?.role === "super_admin" ? selectedTenant : undefined;
    const streamUrl = api.streamIngestUrl(url, maxPages, tid);
    const es = new EventSource(streamUrl);
    esRef.current = es;

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        switch (data.stage) {
          case "start":
            pushLog("start", `Crawl initialisé · max ${data.max_pages} pages`);
            break;
          case "scrape_start":
            pushLog("scrape", data.message);
            break;
          case "scrape_done":
            pushLog("scrape_done", `${data.count} pages collectées`, "success");
            setProgress({ current: 0, total: data.count });
            break;
          case "ingest_page":
            pushLog("ingest", `[${data.index}/${data.total}] ${data.title || data.url}`);
            setProgress({ current: data.index, total: data.total });
            break;
          case "embed":
            pushLog("embed", `Vectorisation · ${data.chunks} chunks`);
            break;
          case "page_done":
            pushLog("ok", `✓ ${data.url} → ${data.chunks} chunks`, "success");
            break;
          case "page_unchanged":
            pushLog("skip", `↻ ${data.url} (inchangé)`);
            break;
          case "page_empty":
            pushLog("skip", `~ ${data.url} (vide)`);
            break;
          case "done":
            pushLog(
              "done",
              `Terminé · ${data.inserted ?? 0} pages, ${data.chunks_total ?? 0} chunks`,
              "success"
            );
            es.close();
            esRef.current = null;
            setRunning(false);
            load(selectedTenant);
            toast({
              tone: "success",
              title: "Ingestion terminée",
              message: `${data.inserted ?? 0} pages traitées`,
            });
            break;
          case "error":
            pushLog("error", data.message, "error");
            es.close();
            esRef.current = null;
            setRunning(false);
            toast({ tone: "error", title: "Erreur", message: data.message });
            break;
        }
      } catch (e) {
        console.error("SSE parse error", e);
      }
    };

    es.onerror = () => {
      pushLog("error", "Connexion SSE interrompue", "error");
      es.close();
      esRef.current = null;
      setRunning(false);
    };
  }

  async function deleteSource(s: Source) {
    const ok = await confirm({
      title: "Supprimer cette source ?",
      message: (
        <>
          La page <strong>{s.title || s.source_url}</strong> et ses{" "}
          <strong>{s.chunks_count} chunks</strong> seront supprimés de la base de connaissances.
        </>
      ),
      confirmText: "Supprimer",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await api.deleteKnowledgeSource(s.id);
      await load(selectedTenant);
      toast({ tone: "info", title: "Source supprimée" });
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  const progressPct =
    progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar
        tenants={tenants}
        selectedTenant={selectedTenant}
        onTenantChange={(id) => {
          setSelectedTenant(id);
          load(id);
        }}
      />
      <FloatingChatButton />

      <main className="lg:pl-64">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="mb-6">
            <div className="text-[10.5px] uppercase tracking-[0.14em] text-primary-600 font-semibold mb-1.5">
              Paramètres
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
              Base de connaissances
            </h1>
            <p className="text-ink-500 mt-1 text-[14px] font-light">
              Sources ingérées par AYA pour répondre aux questions des sociétaires.
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <StatCard label="Sources" value={stats.sources} />
            <StatCard label="Chunks vectorisés" value={stats.chunks} />
          </div>

          {/* Form ingestion */}
          <div className="bg-white border border-ink-100 rounded-sm p-5 mb-6">
            <div className="text-[12px] uppercase tracking-[0.14em] text-ink-500 font-semibold mb-3">
              Lancer un scraping
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={running}
                placeholder="https://www.ma2e.ci/"
                className="flex-1 bg-ink-50 hover:bg-white focus:bg-white border border-ink-200 focus:border-primary-500 rounded-sm px-3 py-2 text-[13px] placeholder:text-ink-400 focus:outline-none transition disabled:opacity-50"
              />
              <input
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                disabled={running}
                min={1}
                max={100}
                className="w-28 bg-ink-50 hover:bg-white focus:bg-white border border-ink-200 focus:border-primary-500 rounded-sm px-3 py-2 text-[13px] focus:outline-none transition disabled:opacity-50"
                placeholder="Max pages"
              />
              <button
                onClick={startIngestion}
                disabled={running}
                className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white text-[13px] font-medium rounded-sm px-4 py-2 transition shadow-sm disabled:cursor-not-allowed"
              >
                {running ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    En cours…
                  </>
                ) : (
                  <>
                    <IconRefresh size={14} />
                    Lancer l'ingestion
                  </>
                )}
              </button>
            </div>
            <div className="text-[11.5px] text-ink-400 font-light mt-2">
              Crawl le site, vectorise via Azure OpenAI (1536 dims), stocke en pgvector.
              Les pages déjà ingérées et inchangées sont ignorées.
            </div>
          </div>

          {/* Progress + Log live */}
          {(running || logs.length > 0) && (
            <div className="bg-ink-900 text-ink-100 border border-ink-800 rounded-sm overflow-hidden mb-6">
              <div className="px-4 py-3 bg-ink-800 border-b border-ink-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      running ? "bg-primary-400 animate-pulse" : "bg-ink-500"
                    }`}
                  />
                  <span className="text-[11.5px] uppercase tracking-[0.14em] font-semibold text-ink-300">
                    {running ? "Stream live" : "Stream terminé"}
                  </span>
                </div>
                {progress.total > 0 && (
                  <div className="text-[11px] text-ink-400 font-mono">
                    {progress.current} / {progress.total} · {progressPct}%
                  </div>
                )}
              </div>
              {progress.total > 0 && (
                <div className="h-1 bg-ink-800">
                  <div
                    className="h-full bg-primary-500 transition-all duration-300"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              )}
              <div
                ref={logRef}
                className="font-mono text-[11.5px] p-4 max-h-72 overflow-y-auto space-y-1 leading-relaxed"
              >
                {logs.map((l, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 ${
                      l.level === "success"
                        ? "text-primary-300"
                        : l.level === "error"
                          ? "text-red-400"
                          : "text-ink-300"
                    }`}
                  >
                    <span className="text-ink-500 shrink-0">{l.ts}</span>
                    <span className="text-ink-500 shrink-0 w-16 text-right">[{l.stage}]</span>
                    <span className="flex-1">{l.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Liste des sources */}
          <div className="bg-white border border-ink-100 rounded-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-ink-100 flex items-center justify-between">
              <div className="text-[12px] uppercase tracking-[0.14em] text-ink-500 font-semibold">
                Sources ingérées · {sources.length}
              </div>
            </div>
            {loading ? (
              <div className="p-12 text-center text-ink-400 text-[13px]">Chargement…</div>
            ) : sources.length === 0 ? (
              <div className="p-12 text-center">
                <div className="text-ink-700 font-medium text-[14px]">Base vide</div>
                <div className="text-ink-500 text-[12.5px] font-light mt-1">
                  Lancez un premier scraping pour peupler la base de connaissances.
                </div>
              </div>
            ) : (
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-[#F9FBFA] text-ink-500 text-[10px] uppercase tracking-[0.1em] font-semibold border-b border-ink-100">
                    <th className="text-left px-4 py-2.5">Page</th>
                    <th className="text-left px-4 py-2.5">Statut</th>
                    <th className="text-left px-4 py-2.5">Chunks</th>
                    <th className="text-left px-4 py-2.5">Dernière mise à jour</th>
                    <th className="text-left px-4 py-2.5 w-12"></th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((s) => (
                    <tr key={s.id} className="border-b border-ink-100 last:border-0">
                      <td className="px-4 py-3 max-w-md">
                        <div className="text-ink-900 font-medium text-[13px] truncate">
                          {s.title || "(sans titre)"}
                        </div>
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-primary-600 hover:underline font-mono truncate block"
                        >
                          {s.source_url}
                        </a>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-[10.5px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-sm border ${
                            STATUS_COLOR[s.status] || "bg-ink-100 text-ink-700 border-ink-200"
                          }`}
                        >
                          {s.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-[12px] text-ink-700">
                        {s.chunks_count}
                      </td>
                      <td className="px-4 py-3 text-[12px] text-ink-500 font-light">
                        {s.last_crawled_at
                          ? new Date(s.last_crawled_at).toLocaleString("fr-FR", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => deleteSource(s)}
                          className="w-7 h-7 flex items-center justify-center text-ink-400 hover:text-red-600 hover:bg-red-50 rounded-sm transition"
                          title="Supprimer"
                        >
                          <IconX size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white border border-ink-100 rounded-sm p-4">
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-500 font-semibold">
        {label}
      </div>
      <div className="text-[28px] leading-none font-semibold tracking-tight text-ink-900 mt-2">
        {value}
      </div>
    </div>
  );
}
