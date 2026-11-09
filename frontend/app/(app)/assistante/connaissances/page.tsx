"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useConfirm, useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";

/**
 * Base de connaissances — version simple :
 *   1. Zone de dépôt de fichiers (PDF/DOCX/XLSX/TXT/MD/CSV) → vectorisation.
 *   2. (Optionnel, repliable) scraping d'une URL de site web.
 *   3. Liste simple des documents indexés, avec taille et suppression.
 *
 * Pas de terminal de logs, pas de double colonne : une page qui respire,
 * dans la même ligne que la page Parcours.
 */

type Source = {
  id: string;
  type: string;
  source_url: string;
  title: string | null;
  chunks_count: number;
  status: string;
  last_crawled_at: string | null;
};

type Toast = ReturnType<typeof useToast>;

export default function KnowledgePage() {
  const confirm = useConfirm();
  const toast = useToast();

  const [sources, setSources] = useState<Source[]>([]);
  const [stats, setStats] = useState<{ sources: number; chunks: number }>({ sources: 0, chunks: 0 });
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [srcs, st] = await Promise.all([
        api.listKnowledgeSources() as Promise<Source[]>,
        api.knowledgeStats() as Promise<{ sources: number; chunks: number }>,
      ]);
      setSources(srcs);
      setStats(st);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur de chargement", message: e?.message ?? "" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function deleteSource(s: Source) {
    const ok = await confirm({
      title: "Supprimer cette source ?",
      message: (
        <>
          <strong>{s.title || prettyUrl(s.source_url)}</strong> et ses{" "}
          <strong>{s.chunks_count} chunks</strong> seront retirés de la base de connaissances.
        </>
      ),
      confirmText: "Supprimer",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await api.deleteKnowledgeSource(s.id);
      toast({ tone: "info", title: "Source supprimée", message: "" });
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e?.message ?? "" });
    }
  }

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <h1 className="sa-page-title">Base de connaissances</h1>
          <p className="sa-page-desc">
            Déposez vos documents : règlement MA2E, guide sociétaire, FAQ, procédures… Chaque
            fichier est automatiquement vectorisé pour que le bot puisse répondre aux
            questions libres en citant son contenu.
          </p>
        </div>
        <div className="sa-page-actions">
          <SummaryBadge icon="database" value={stats.sources} label="documents" />
          <SummaryBadge icon="dashboard-square-01" value={stats.chunks} label="chunks" />
        </div>
      </header>

      <FileUploadCard onDone={reload} toast={toast} />

      <UrlIngestCard onDone={reload} toast={toast} />

      <SourcesCard
        loading={loading}
        sources={sources}
        onDelete={deleteSource}
      />
    </>
  );
}

/* --------------------------------------------------------------------- */
/* Résumé top-right                                                      */
/* --------------------------------------------------------------------- */

function SummaryBadge({ icon, value, label }: { icon: string; value: number; label: string }) {
  return (
    <div
      className="sa-row"
      style={{
        gap: 8,
        padding: "8px 12px",
        border: "1px solid rgb(var(--color-border-default))",
        borderRadius: 8,
        alignItems: "center",
      }}
    >
      <Icon name={icon} className="i" style={{ opacity: 0.6 }} />
      <div>
        <div style={{ fontWeight: 600, lineHeight: 1 }}>{value.toLocaleString("fr-FR")}</div>
        <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase", letterSpacing: 0.3 }}>
          {label}
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------- */
/* Upload de fichiers                                                    */
/* --------------------------------------------------------------------- */

function FileUploadCard({
  onDone,
  toast,
}: {
  onDone: () => Promise<void> | void;
  toast: Toast;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [dragOver, setDragOver] = useState(false);

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (!list.length) return;
    setUploading(true);
    setProgress({ done: 0, total: list.length });
    let ok = 0;
    for (let i = 0; i < list.length; i++) {
      try {
        const res = await api.uploadKnowledgeFile(list[i]);
        ok++;
        toast({
          tone: "success",
          title: list[i].name,
          message: `${res.chunks_count} chunks indexés`,
        });
      } catch (e: any) {
        toast({
          tone: "error",
          title: list[i].name,
          message: e?.message?.replace(/^\d+:\s*/, "") ?? "Échec de l'upload.",
        });
      }
      setProgress({ done: i + 1, total: list.length });
    }
    setUploading(false);
    setTimeout(() => setProgress(null), 1200);
    if (inputRef.current) inputRef.current.value = "";
    if (ok > 0) await onDone();
  }

  return (
    <section className="sa-card">
      <div className="sa-card__header">
        <h2 className="sa-card__title">Déposer des documents</h2>
        <p className="sa-card__desc">
          PDF, Word, Excel, texte, Markdown, CSV — plusieurs à la fois. 20 Mo par fichier.
        </p>
      </div>
      <label
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (!uploading) void handleFiles(e.dataTransfer.files);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: 36,
          border: `2px dashed rgb(var(--color-${dragOver ? "brand-primary" : "border-default"}))`,
          borderRadius: 12,
          background: dragOver
            ? "rgb(var(--color-brand-primary) / 0.06)"
            : "rgb(var(--color-bg-subtle) / 0.4)",
          cursor: uploading ? "wait" : "pointer",
          transition: "border-color 150ms, background 150ms",
        }}
      >
        <Icon
          name={uploading ? "loading-03" : "cloud-upload"}
          className="i"
          style={{ width: 44, height: 44, opacity: 0.6 }}
        />
        <div style={{ marginTop: 10, fontWeight: 500 }}>
          {uploading
            ? `Indexation en cours… (${progress?.done ?? 0}/${progress?.total ?? 0})`
            : "Glissez vos fichiers ici ou cliquez pour parcourir"}
        </div>
        <div style={{ marginTop: 4, fontSize: 13, opacity: 0.65 }}>
          Formats acceptés : PDF · DOCX · XLSX · TXT · MD · CSV
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.xlsx,.txt,.md,.csv"
          style={{ display: "none" }}
          disabled={uploading}
          onChange={(e) => {
            if (e.target.files?.length) void handleFiles(e.target.files);
          }}
        />
      </label>
    </section>
  );
}

/* --------------------------------------------------------------------- */
/* Scraping URL — bouton d'ouverture + modal                              */
/* --------------------------------------------------------------------- */

function UrlIngestCard({
  onDone,
  toast,
}: {
  onDone: () => Promise<void> | void;
  toast: Toast;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <section className="sa-card">
        <div
          className="sa-row"
          style={{ alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}
        >
          <div>
            <h2 className="sa-card__title" style={{ marginBottom: 2 }}>
              Indexer un site web
            </h2>
            <p className="sa-card__desc" style={{ margin: 0 }}>
              Alternative à l&apos;upload : donnez une URL, le bot crawle le site et indexe
              chaque page.
            </p>
          </div>
          <button
            type="button"
            className="sa-btn sa-btn--outline"
            onClick={() => setOpen(true)}
          >
            <Icon name="link-02" className="i" />
            Lancer un scraping
          </button>
        </div>
      </section>
      {open && (
        <UrlIngestModal
          onClose={() => setOpen(false)}
          onDone={async () => {
            await onDone();
          }}
          toast={toast}
        />
      )}
    </>
  );
}

function UrlIngestModal({
  onClose,
  onDone,
  toast,
}: {
  onClose: () => void;
  onDone: () => Promise<void> | void;
  toast: Toast;
}) {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(30);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ seen: number; total: number } | null>(null);
  const [currentPage, setCurrentPage] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  // Échappement = fermer (sauf en cours d'ingestion).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !running) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, running]);

  // Nettoyage de l'EventSource au démontage.
  useEffect(() => {
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, []);

  async function startStream() {
    if (!url.trim()) return;
    setRunning(true);
    setProgress(null);
    setCurrentPage(null);
    const streamUrl = api.streamIngestUrl(url, maxPages);
    const es = new EventSource(streamUrl, { withCredentials: true });
    esRef.current = es;
    let inserted = 0;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.stage === "scrape_page") {
          setProgress({ seen: 0, total: data.index ?? 0 });
          setCurrentPage(data.title || data.url || null);
        } else if (data.stage === "scrape_done") {
          setProgress({ seen: 0, total: data.count ?? 0 });
        } else if (data.stage === "ingest_page") {
          setProgress({ seen: data.index ?? 0, total: data.total ?? 0 });
          setCurrentPage(data.title || data.url || null);
        } else if (data.stage === "page_done") {
          inserted++;
        } else if (data.stage === "done") {
          es.close();
          esRef.current = null;
          setRunning(false);
          toast({
            tone: "success",
            title: "Ingestion terminée",
            message: `${data.inserted ?? inserted} pages indexées`,
          });
          void onDone();
          onClose();
        } else if (data.stage === "error") {
          es.close();
          esRef.current = null;
          setRunning(false);
          toast({ tone: "error", title: "Erreur", message: data.message ?? "" });
        }
      } catch {
        /* parse ignoré */
      }
    };
    es.onerror = () => {
      es.close();
      esRef.current = null;
      setRunning(false);
      toast({ tone: "error", title: "Connexion interrompue", message: "" });
    };
  }

  const percent =
    progress && progress.total > 0 ? Math.round((progress.seen / progress.total) * 100) : 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="scrape-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !running) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        zIndex: 200,
      }}
    >
      <div
        className="sa-card"
        style={{
          background: "rgb(var(--color-bg-surface))",
          maxWidth: 540,
          width: "100%",
          boxShadow: "0 20px 48px -8px rgba(0, 0, 0, 0.35)",
          border: "1px solid rgb(var(--color-border-default))",
        }}
      >
        <div
          className="sa-row"
          style={{ alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}
        >
          <div>
            <h2 id="scrape-modal-title" className="sa-card__title" style={{ marginBottom: 2 }}>
              Indexer un site web
            </h2>
            <p className="sa-card__desc" style={{ margin: 0 }}>
              Le bot crawle le site, extrait le texte de chaque page et le vectorise.
            </p>
          </div>
          <button
            type="button"
            className="sa-icon-btn"
            onClick={onClose}
            disabled={running}
            aria-label="Fermer"
            style={{ width: 32, height: 32 }}
          >
            <Icon name="cancel-01" className="i" />
          </button>
        </div>

        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <label>
            <div className="sa-cell-sub" style={{ marginBottom: 4 }}>
              URL du site
            </div>
            <input
              type="url"
              className="sa-input"
              placeholder="https://www.exemple.ci/"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={running}
              autoFocus
            />
          </label>
          <label>
            <div className="sa-cell-sub" style={{ marginBottom: 4 }}>
              Nombre de pages maximum
            </div>
            <input
              type="number"
              min={1}
              max={100}
              className="sa-input"
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value) || 30)}
              disabled={running}
              style={{ maxWidth: 160 }}
            />
          </label>

          {running && (
            <div style={{ marginTop: 4 }}>
              <div className="sa-cell-sub" style={{ marginBottom: 6 }}>
                {progress
                  ? `Page ${progress.seen}/${progress.total}${currentPage ? ` · ${currentPage}` : ""}`
                  : "Analyse du site en cours…"}
              </div>
              <div
                style={{
                  height: 6,
                  borderRadius: 999,
                  background: "rgb(var(--color-bg-subtle))",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${percent}%`,
                    height: "100%",
                    background: "rgb(var(--color-brand-primary))",
                    transition: "width 200ms ease",
                  }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="sa-row" style={{ gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
          <button
            type="button"
            className="sa-btn sa-btn--ghost"
            onClick={onClose}
            disabled={running}
          >
            Annuler
          </button>
          <button
            type="button"
            className="sa-btn sa-btn--primary"
            onClick={startStream}
            disabled={running || !url.trim()}
          >
            {running ? "Ingestion en cours…" : "Lancer l'ingestion"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------- */
/* Liste des sources                                                     */
/* --------------------------------------------------------------------- */

function SourcesCard({
  loading,
  sources,
  onDelete,
}: {
  loading: boolean;
  sources: Source[];
  onDelete: (s: Source) => void;
}) {
  return (
    <section className="sa-card">
      <div className="sa-card__header">
        <h2 className="sa-card__title">Sources indexées</h2>
        <p className="sa-card__desc">
          Documents et pages que le bot utilise pour répondre aux questions libres.
        </p>
      </div>

      {loading ? (
        <div style={{ padding: 32, display: "flex", justifyContent: "center" }}>
          <span className="sa-spinner" role="status" aria-label="Chargement" />
        </div>
      ) : sources.length === 0 ? (
        <div className="sa-empty">
          <Icon name="database" className="i" />
          <div className="sa-empty__title">Base vide</div>
          <p className="sa-empty__text">
            Déposez votre premier document ci-dessus pour que le bot puisse y puiser ses
            réponses.
          </p>
        </div>
      ) : (
        <div className="sa-table-wrap">
          <table className="sa-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Type</th>
                <th className="hidden md:table-cell">Chunks</th>
                <th className="hidden md:table-cell">Ajouté le</th>
                <th>Statut</th>
                <th className="is-tight">
                  <span className="sa-sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <SourceRow key={s.id} s={s} onDelete={onDelete} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SourceRow({ s, onDelete }: { s: Source; onDelete: (s: Source) => void }) {
  const label = s.title || prettyUrl(s.source_url);
  const isFile = s.type === "file" || s.source_url.startsWith("file://");
  return (
    <tr>
      <td data-label="Document">
        <div className="sa-row" style={{ gap: 8, alignItems: "center" }}>
          <Icon name={isFile ? "file-01" : "link-02"} className="i" style={{ opacity: 0.6 }} />
          <span className="sa-cell-main">{label}</span>
        </div>
      </td>
      <td data-label="Type">
        <span className="sa-badge">{isFile ? "Fichier" : "Page web"}</span>
      </td>
      <td className="hidden md:table-cell" data-label="Chunks">
        <span className="sa-mono">{s.chunks_count}</span>
      </td>
      <td className="hidden md:table-cell" data-label="Ajouté le">
        <span className="sa-cell-sub" style={{ whiteSpace: "nowrap" }}>
          {s.last_crawled_at
            ? new Date(s.last_crawled_at).toLocaleDateString("fr-FR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
              })
            : "—"}
        </span>
      </td>
      <td data-label="Statut">
        <StatusBadge status={s.status} />
      </td>
      <td className="is-tight">
        <button
          type="button"
          className="sa-icon-btn"
          onClick={() => onDelete(s)}
          aria-label="Supprimer"
          style={{ width: 32, height: 32 }}
        >
          <Icon name="delete-02" className="i" />
        </button>
      </td>
    </tr>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    ready: { cls: "sa-badge--ok", label: "Prête" },
    ingesting: { cls: "sa-badge--warn", label: "Indexation" },
    empty: { cls: "", label: "Vide" },
    pending: { cls: "", label: "En attente" },
  };
  const s = map[status] ?? { cls: "", label: status };
  return <span className={`sa-badge ${s.cls}`}>{s.label}</span>;
}

function prettyUrl(url: string) {
  if (url.startsWith("file://")) return url.replace(/^file:\/\//, "");
  try {
    const u = new URL(url);
    return u.hostname + u.pathname;
  } catch {
    return url;
  }
}
