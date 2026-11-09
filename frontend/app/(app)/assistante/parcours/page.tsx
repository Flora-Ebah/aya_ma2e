"use client";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";

/**
 * Pilotage du parcours IA — modal « Créer un parcours » + extraction LLM.
 *
 * L'admin clique « Créer un parcours » → modal (nom, description, fichier
 * Word/PDF/TXT) → extraction LLM → aperçu structuré en bas de page →
 * bouton Appliquer qui envoie le JSON (potentiellement avec nom/description
 * surchargés) au backend.
 */

type Diff = {
  name: string;
  language: string;
  description: string;
  steps_count: number;
  messages_count: number;
  added_steps: string[];
  removed_steps: string[];
  modified_steps: string[];
  added_messages: string[];
  removed_messages: string[];
  modified_messages: string[];
  is_empty: boolean;
};

type Step = {
  order: number;
  code: string;
  label: string;
  type: string;
  question: string | null;
  template_code: string | null;
  action_name: string | null;
  next_step_code: string | null;
  branches: Record<string, string>;
  validation_rules: Record<string, any>;
};

type ParcoursDoc = {
  meta: { name: string; description: string; language: string };
  steps: Step[];
  messages: Record<string, string>;
};

type Version = {
  id: string;
  name: string;
  description: string | null;
  version: number;
  active: boolean;
  steps_count: number;
  created_at: string;
  updated_at: string;
};

const ACCEPTED = ".docx,.pdf,.txt,.md";
const ACCEPTED_EXT = /\.(docx|pdf|txt|md)$/i;

export default function ParcoursPage() {
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [pending, setPending] = useState<{ document: ParcoursDoc; diff: Diff; filename: string } | null>(null);
  const [applying, setApplying] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error" | "info"; text: string } | null>(
    null,
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [docsCache, setDocsCache] = useState<Record<string, ParcoursDoc>>({});
  const [docLoading, setDocLoading] = useState<string | null>(null);

  async function toggleExpand(id: string) {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (docsCache[id]) return;
    setDocLoading(id);
    try {
      const doc = await api.getParcoursVersionDocument(id);
      setDocsCache((prev) => ({ ...prev, [id]: doc }));
    } catch (e: any) {
      setToast({ type: "error", text: "Erreur : " + (e?.message ?? "") });
      setExpandedId(null);
    } finally {
      setDocLoading(null);
    }
  }

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listParcoursVersions();
      setVersions(list);
    } catch (e: any) {
      setError(e?.message ?? "Erreur de chargement.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  async function applyPending() {
    if (!pending) return;
    setApplying(true);
    try {
      await api.applyParcoursDocument(pending.document);
      setToast({ type: "success", text: "Nouvelle version appliquée et activée." });
      setPending(null);
      await reload();
    } catch (e: any) {
      setToast({ type: "error", text: "Erreur : " + (e?.message?.replace(/^\d+:\s*/, "") ?? "") });
    } finally {
      setApplying(false);
    }
  }

  async function activateVersion(id: string) {
    try {
      await api.activateParcoursVersion(id);
      setToast({ type: "success", text: "Version activée." });
      await reload();
    } catch (e: any) {
      setToast({ type: "error", text: "Erreur : " + (e?.message?.replace(/^\d+:\s*/, "") ?? "") });
    }
  }

  async function deleteVersion(id: string, isActive: boolean) {
    const msg = isActive
      ? "Cette version est ACTIVE. La supprimer stoppera le chatbot tant qu'une autre version n'est pas activée. Continuer ?"
      : "Supprimer définitivement cette version ?";
    if (!confirm(msg)) return;
    try {
      await api.deleteParcoursVersion(id);
      setToast({ type: "success", text: "Version supprimée." });
      await reload();
    } catch (e: any) {
      setToast({ type: "error", text: "Erreur : " + (e?.message?.replace(/^\d+:\s*/, "") ?? "") });
    }
  }

  const active = versions.find((v) => v.active);

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <h1 className="sa-page-title">Parcours du chatbot</h1>
          <p className="sa-page-desc">
            Décrivez votre parcours dans un document Word / PDF (titre + liste des questions).
            L&apos;IA en déduit le parcours structuré, vous le validez, il est activé.
          </p>
        </div>
        <div className="sa-page-actions">
          <button
            type="button"
            className="sa-btn sa-btn--primary"
            onClick={() => setModalOpen(true)}
          >
            <Icon name="add-01" className="i" />
            Créer un parcours
          </button>
        </div>
      </header>

      {/* -- Version active -- */}
      <section className="sa-card" aria-label="Version active">
        <div className="sa-card__header">
          <div>
            <h2 className="sa-card__title">Parcours actif</h2>
            <p className="sa-card__desc">Version jouée par le bot WhatsApp et le chat web.</p>
          </div>
        </div>
        {loading ? (
          <div className="sa-skeleton sa-skeleton--text" style={{ width: 220 }} />
        ) : active ? (
          <div className="sa-grid sa-grid--kpi" style={{ gap: 12 }}>
            <Kpi label="Nom" value={active.name} icon="hierarchy-square-02" />
            <Kpi label="Version" value={`v${active.version}`} icon="layers-01" />
            <Kpi label="Étapes" value={String(active.steps_count)} icon="dashboard-square-01" />
            <Kpi
              label="Dernière mise à jour"
              value={new Date(active.updated_at).toLocaleString("fr-FR", {
                dateStyle: "short",
                timeStyle: "short",
              })}
              icon="clock-01"
            />
          </div>
        ) : (
          <div className="sa-empty">
            <Icon name="hierarchy-square-02" className="i" />
            <div className="sa-empty__title">Aucun parcours actif</div>
            <p className="sa-empty__text">
              Cliquez sur « Créer un parcours » pour en déposer un.
            </p>
          </div>
        )}
      </section>

      {/* -- Preview après extraction -- */}
      {pending && (
        <section className="sa-card" aria-label="Parcours extrait">
          <ExtractionPreview
            data={pending}
            applying={applying}
            onCancel={() => setPending(null)}
            onApply={applyPending}
          />
        </section>
      )}

      {/* -- Historique -- */}
      <section className="sa-card" aria-label="Historique des versions">
        <div className="sa-card__header">
          <h2 className="sa-card__title">Historique</h2>
          <p className="sa-card__desc">
            Chaque création produit une nouvelle version ; vous pouvez en réactiver une à tout moment.
          </p>
        </div>
        {error && (
          <div className="sa-alert sa-alert--error" role="alert">
            <Icon name="alert-circle" className="i" />
            <div className="sa-alert__body">
              <p className="sa-alert__text">{error}</p>
            </div>
          </div>
        )}
        {loading ? (
          <div>Chargement…</div>
        ) : versions.length === 0 ? (
          <div className="sa-empty">
            <Icon name="layers-01" className="i" />
            <div className="sa-empty__title">Aucune version pour le moment</div>
          </div>
        ) : (
          <div className="sa-table-wrap">
            <table className="sa-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Nom</th>
                  <th>Étapes</th>
                  <th>Mis à jour le</th>
                  <th>Statut</th>
                  <th className="is-tight">
                    <span className="sa-sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => {
                  const isOpen = expandedId === v.id;
                  return (
                    <Fragment key={v.id}>
                      <tr
                        onClick={() => toggleExpand(v.id)}
                        style={{ cursor: "pointer" }}
                        aria-expanded={isOpen}
                      >
                        <td className="sa-mono">
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                            <Icon
                              name={isOpen ? "arrow-down-01" : "arrow-right-01"}
                              className="i"
                            />
                            v{v.version}
                          </span>
                        </td>
                        <td>{v.name}</td>
                        <td>{v.steps_count}</td>
                        <td>
                          {new Date(v.updated_at).toLocaleString("fr-FR", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })}
                        </td>
                        <td>
                          {v.active ? (
                            <span className="sa-badge sa-badge--ok">
                              <Icon name="tick-02" className="i" /> Active
                            </span>
                          ) : (
                            <span className="sa-badge">Archivée</span>
                          )}
                        </td>
                        <td className="is-tight" onClick={(e) => e.stopPropagation()}>
                          <div className="sa-row" style={{ gap: 4, justifyContent: "flex-end" }}>
                            {!v.active && (
                              <button
                                type="button"
                                className="sa-btn sa-btn--outline sa-btn--sm"
                                onClick={() => activateVersion(v.id)}
                              >
                                Réactiver
                              </button>
                            )}
                            <button
                              type="button"
                              className="sa-icon-btn"
                              onClick={() => deleteVersion(v.id, v.active)}
                              aria-label="Supprimer"
                              title="Supprimer"
                              style={{ width: 32, height: 32 }}
                            >
                              <Icon name="delete-02" className="i" />
                            </button>
                          </div>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="sa-table__expand-row">
                          <td colSpan={6} style={{ padding: 0, background: "rgb(var(--color-bg-subtle))" }}>
                            {docLoading === v.id ? (
                              <div style={{ padding: 16, color: "rgb(var(--color-text-soft))" }}>
                                Chargement du contenu…
                              </div>
                            ) : docsCache[v.id] ? (
                              <ParcoursDetails doc={docsCache[v.id]} />
                            ) : null}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {modalOpen && (
        <CreateParcoursModal
          onClose={() => setModalOpen(false)}
          onExtracted={(res) => {
            setPending(res);
            setModalOpen(false);
            setToast({
              type: "info",
              text: "Parcours extrait. Vérifiez le résultat ci-dessous.",
            });
          }}
        />
      )}

      {toast && <TopToast toast={toast} onClose={() => setToast(null)} />}
    </>
  );
}

function ParcoursDetails({ doc }: { doc: ParcoursDoc }) {
  const [showMessages, setShowMessages] = useState(false);
  const typeMeta: Record<string, { label: string; icon: string; color: string }> = {
    message: { label: "Message", icon: "message-01", color: "#64748b" },
    question: { label: "Question", icon: "help-circle", color: "#0ea5e9" },
    action: { label: "Action", icon: "settings-02", color: "#f59e0b" },
    decision: { label: "Décision", icon: "git-branch", color: "#a855f7" },
  };

  const messageCount = Object.keys(doc.messages || {}).length;

  return (
    <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 20 }}>
      {/* En-tête — méta */}
      {doc.meta.description && (
        <div
          style={{
            padding: 12,
            background: "rgb(var(--color-bg-surface))",
            borderRadius: 8,
            borderLeft: "3px solid rgb(var(--color-action-primary))",
            fontSize: 13,
            color: "rgb(var(--color-text-strong))",
          }}
        >
          {doc.meta.description}
        </div>
      )}

      {/* Timeline des steps */}
      <div>
        <div
          className="sa-strong"
          style={{ fontSize: 13, marginBottom: 10, color: "rgb(var(--color-text-soft))" }}
        >
          Déroulé du parcours ({doc.steps.length} étapes)
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {doc.steps.map((s, idx) => {
            const t = typeMeta[s.type] || typeMeta.message;
            const rules = s.validation_rules || {};
            const formFields = Array.isArray(rules.form_fields) ? rules.form_fields : null;
            const optionsRef = rules.options_ref as string | undefined;
            return (
              <div
                key={s.code}
                style={{
                  display: "grid",
                  gridTemplateColumns: "28px 1fr",
                  gap: 12,
                  alignItems: "start",
                }}
              >
                {/* Timeline bullet */}
                <div
                  style={{
                    position: "relative",
                    minHeight: 60,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 999,
                      background: t.color,
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    {idx + 1}
                  </div>
                  {idx < doc.steps.length - 1 && (
                    <div
                      style={{
                        flex: 1,
                        width: 2,
                        marginTop: 4,
                        background: "rgb(var(--color-border))",
                      }}
                    />
                  )}
                </div>

                {/* Card */}
                <div
                  style={{
                    background: "rgb(var(--color-bg-surface))",
                    border: "1px solid rgb(var(--color-border))",
                    borderRadius: 8,
                    padding: "10px 14px",
                  }}
                >
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        letterSpacing: 0.2,
                        color: t.color,
                        textTransform: "uppercase",
                      }}
                    >
                      {t.label}
                    </span>
                    <span className="sa-strong" style={{ fontSize: 14 }}>
                      {s.label}
                    </span>
                  </div>
                  {(s as any).description && (
                    <div
                      style={{
                        fontSize: 13,
                        color: "rgb(var(--color-text-soft))",
                        marginTop: 4,
                      }}
                    >
                      {(s as any).description}
                    </div>
                  )}

                  {s.action_name && (
                    <div
                      style={{
                        marginTop: 6,
                        fontSize: 12,
                        color: "rgb(var(--color-text-soft))",
                      }}
                    >
                      Action backend : <code>{s.action_name}</code>
                    </div>
                  )}

                  {optionsRef && (
                    <div
                      style={{
                        marginTop: 6,
                        fontSize: 12,
                        color: "rgb(var(--color-text-soft))",
                      }}
                    >
                      Choix depuis la liste <code>{optionsRef}</code>
                    </div>
                  )}

                  {formFields && formFields.length > 0 && (
                    <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {formFields.map((f: any) => (
                        <span
                          key={f.key || f.name || f.label}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "3px 8px",
                            background: "rgb(var(--color-bg-subtle))",
                            borderRadius: 4,
                            fontSize: 11,
                            color: "rgb(var(--color-text-strong))",
                          }}
                        >
                          {f.label || f.key || f.name}
                          {f.optional && (
                            <span style={{ color: "rgb(var(--color-text-soft))", fontStyle: "italic" }}>
                              facultatif
                            </span>
                          )}
                          {f.options_ref && (
                            <span style={{ color: t.color }}>↗ {f.options_ref}</span>
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Messages — section repliable */}
      {messageCount > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowMessages((v) => !v)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "transparent",
              border: 0,
              font: "inherit",
              fontSize: 13,
              color: "rgb(var(--color-text-strong))",
              cursor: "pointer",
              padding: 0,
            }}
          >
            <Icon name={showMessages ? "arrow-down-01" : "arrow-right-01"} className="i" />
            <span className="sa-strong">Templates de messages ({messageCount})</span>
          </button>

          {showMessages && (
            <div
              style={{
                marginTop: 10,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                gap: 8,
              }}
            >
              {Object.entries(doc.messages).map(([code, content]) => (
                <div
                  key={code}
                  style={{
                    padding: 10,
                    background: "rgb(var(--color-bg-surface))",
                    borderRadius: 6,
                    border: "1px solid rgb(var(--color-border))",
                    fontSize: 12,
                  }}
                >
                  <div
                    className="sa-mono"
                    style={{
                      fontSize: 11,
                      color: "rgb(var(--color-text-soft))",
                      marginBottom: 6,
                    }}
                  >
                    {code}
                  </div>
                  <div
                    style={{
                      whiteSpace: "pre-wrap",
                      color: "rgb(var(--color-text-strong))",
                      maxHeight: 140,
                      overflow: "auto",
                    }}
                  >
                    {content}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TopToast({
  toast,
  onClose,
}: {
  toast: { type: "success" | "error" | "info"; text: string };
  onClose: () => void;
}) {
  const palette: Record<string, { bg: string; border: string; icon: string }> = {
    success: {
      bg: "rgb(var(--color-feedback-success-subtle, 232 250 236))",
      border: "rgb(var(--color-feedback-success, 0 160 69))",
      icon: "tick-02",
    },
    error: {
      bg: "rgb(var(--color-feedback-error-subtle, 253 232 232))",
      border: "rgb(var(--color-feedback-error, 220 38 38))",
      icon: "alert-circle",
    },
    info: {
      bg: "rgb(var(--color-feedback-info-subtle, 232 240 253))",
      border: "rgb(var(--color-feedback-info, 29 109 230))",
      icon: "information-circle",
    },
  };
  const p = palette[toast.type];
  return (
    <div
      role="status"
      style={{
        position: "fixed",
        top: 16,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        zIndex: 100,
      }}
    >
      <div
        style={{
          background: "rgb(var(--color-bg-surface))",
          borderLeft: `4px solid ${p.border}`,
          padding: "12px 16px",
          borderRadius: 10,
          boxShadow: "0 12px 32px -8px rgba(0,0,0,0.35)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          minWidth: 320,
          maxWidth: 560,
          pointerEvents: "auto",
        }}
      >
        <Icon name={p.icon} className="i" style={{ color: p.border }} />
        <div style={{ flex: 1, fontSize: 14 }}>{toast.text}</div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer"
          className="sa-icon-btn"
          style={{ width: 28, height: 28 }}
        >
          <Icon name="cancel-01" className="i" />
        </button>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Modal
// ------------------------------------------------------------------

function CreateParcoursModal({
  onClose,
  onExtracted,
}: {
  onClose: () => void;
  onExtracted: (res: { document: ParcoursDoc; diff: Diff; filename: string }) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  function pickFile(f: File | null | undefined) {
    setErr(null);
    if (!f) return;
    if (!ACCEPTED_EXT.test(f.name)) {
      setErr("Formats acceptés : Word (.docx), PDF (.pdf), texte (.txt, .md).");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setErr("Fichier trop volumineux (10 Mo max).");
      return;
    }
    setFile(f);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!file) {
      setErr("Déposez un document (.docx, .pdf, .txt, .md).");
      return;
    }
    setBusy(true);
    try {
      const res = await api.extractParcoursUpload(file);
      // Surcharge le nom et la description si l'admin les a renseignés
      if (name.trim()) res.document.meta.name = name.trim();
      if (description.trim()) res.document.meta.description = description.trim();
      onExtracted({ document: res.document, diff: res.diff, filename: file.name });
    } catch (e: any) {
      setErr(e?.message?.replace(/^\d+:\s*/, "") ?? "Extraction impossible.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={backdropStyle} onClick={() => !busy && onClose()}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-parcours-title"
        style={modalStyle}
        onClick={(e) => e.stopPropagation()}
      >
        <header style={{ padding: "20px 24px 0", display: "flex", justifyContent: "space-between" }}>
          <div>
            <h2 id="create-parcours-title" className="sa-h4" style={{ margin: 0 }}>
              Créer un parcours
            </h2>
            <p className="sa-page-desc" style={{ margin: "4px 0 0" }}>
              L&apos;IA transforme votre document en parcours jouable par le chatbot.
            </p>
          </div>
          <button
            type="button"
            className="sa-icon-btn"
            onClick={onClose}
            disabled={busy}
            aria-label="Fermer"
            style={{ width: 32, height: 32 }}
          >
            <Icon name="cancel-01" className="i" />
          </button>
        </header>

        <form onSubmit={submit} style={{ padding: "16px 24px 24px" }}>
          <div style={{ marginBottom: 12 }}>
            <label className="sa-label" htmlFor="pc-name">
              Nom du parcours <span style={{ opacity: 0.5 }}>(optionnel)</span>
            </label>
            <input
              id="pc-name"
              type="text"
              className="sa-input"
              placeholder="Ex. Inscription sociétaire 2026"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={busy}
              maxLength={120}
            />
            <p className="sa-help">Si vide, l&apos;IA reprend le titre présent dans le document.</p>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label className="sa-label" htmlFor="pc-desc">
              Description <span style={{ opacity: 0.5 }}>(optionnel)</span>
            </label>
            <textarea
              id="pc-desc"
              className="sa-input"
              placeholder="Phrase d'intro visible dans l'historique."
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={busy}
              maxLength={300}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label className="sa-label">Document source</label>
            <label
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: 24,
                border: "2px dashed rgb(var(--color-border-default))",
                borderRadius: 10,
                cursor: busy ? "not-allowed" : "pointer",
                background: "rgb(var(--color-bg-subtle) / 0.4)",
                opacity: busy ? 0.6 : 1,
              }}
              onDragOver={(e) => {
                e.preventDefault();
              }}
              onDrop={(e) => {
                e.preventDefault();
                if (busy) return;
                pickFile(e.dataTransfer.files?.[0]);
              }}
            >
              {file ? (
                <>
                  <Icon name="file-01" className="i" style={{ width: 32, height: 32, opacity: 0.7 }} />
                  <div style={{ marginTop: 6, fontWeight: 500 }}>{file.name}</div>
                  <div style={{ fontSize: 12, opacity: 0.6, marginTop: 2 }}>
                    {(file.size / 1024).toFixed(0)} Ko · cliquer pour changer
                  </div>
                </>
              ) : (
                <>
                  <Icon name="cloud-upload" className="i" style={{ width: 32, height: 32, opacity: 0.6 }} />
                  <div style={{ marginTop: 6, fontWeight: 500 }}>
                    Glissez ou cliquez pour choisir un fichier
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.6, marginTop: 2 }}>
                    Word · PDF · texte — 10 Mo max
                  </div>
                </>
              )}
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED}
                style={{ display: "none" }}
                disabled={busy}
                onChange={(e) => pickFile(e.target.files?.[0])}
              />
            </label>
          </div>

          {err && (
            <div className="sa-alert sa-alert--error" role="alert" style={{ marginBottom: 12 }}>
              <Icon name="alert-circle" className="i" />
              <div className="sa-alert__body">
                <p className="sa-alert__text" style={{ whiteSpace: "pre-line" }}>
                  {err}
                </p>
              </div>
            </div>
          )}

          {busy && (
            <div
              className="sa-alert sa-alert--info"
              role="status"
              style={{ marginBottom: 12 }}
            >
              <Icon name="loading-03" className="i" />
              <div className="sa-alert__body">
                <p className="sa-alert__text">
                  Analyse par l&apos;IA en cours… (10-30 secondes selon la taille du document)
                </p>
              </div>
            </div>
          )}

          <div className="sa-row" style={{ gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="sa-btn sa-btn--ghost"
              onClick={onClose}
              disabled={busy}
            >
              Annuler
            </button>
            <button
              type="submit"
              className="sa-btn sa-btn--primary"
              disabled={busy || !file}
            >
              {busy ? "Extraction…" : "Analyser le document"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const backdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 16,
  zIndex: 200,
};

const modalStyle: React.CSSProperties = {
  background: "rgb(var(--color-bg-surface))",
  border: "1px solid rgb(var(--color-border-default))",
  borderRadius: 14,
  width: "100%",
  maxWidth: 560,
  maxHeight: "90vh",
  overflowY: "auto",
  boxShadow: "0 20px 48px -8px rgba(0,0,0,0.5)",
};

// ------------------------------------------------------------------
// KPI + Preview
// ------------------------------------------------------------------

function Kpi({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="sa-card sa-card--interactive" style={{ padding: 16 }}>
      <div className="sa-row" style={{ gap: 10, alignItems: "center" }}>
        <Icon name={icon} className="i" style={{ opacity: 0.6 }} />
        <div className="sa-cell-sub" style={{ textTransform: "uppercase", fontSize: 11, letterSpacing: 0.4 }}>
          {label}
        </div>
      </div>
      <div style={{ marginTop: 6, fontSize: 18, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function ChangeChip({
  color,
  count,
  label,
}: {
  color: "success" | "warn" | "error" | "info";
  count: number;
  label: string;
}) {
  const map: Record<string, string> = {
    success: "sa-badge--ok",
    warn: "sa-badge--warn",
    error: "sa-badge--error",
    info: "sa-badge--info",
  };
  return (
    <div className="sa-card" style={{ padding: 12, textAlign: "center" }}>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{count}</div>
      <div style={{ marginTop: 4 }}>
        <span className={`sa-badge ${map[color]}`}>{label}</span>
      </div>
    </div>
  );
}

function ExtractionPreview({
  data,
  applying,
  onCancel,
  onApply,
}: {
  data: { document: ParcoursDoc; diff: Diff; filename: string };
  applying: boolean;
  onCancel: () => void;
  onApply: () => void;
}) {
  const { document: doc, diff } = data;
  return (
    <>
      <div className="sa-card__header">
        <div>
          <div className="sa-row" style={{ gap: 8, alignItems: "center" }}>
            <Icon name="sparkles" className="i" style={{ color: "rgb(var(--color-brand-accent))" }} />
            <h2 className="sa-card__title" style={{ margin: 0 }}>
              Parcours extrait depuis « {data.filename} »
            </h2>
          </div>
          <p className="sa-card__desc">
            <strong>{doc.meta.name}</strong>
            {doc.meta.description ? ` — ${doc.meta.description}` : ""}
          </p>
        </div>
      </div>

      <div className="sa-grid sa-grid--kpi" style={{ gap: 12, marginBottom: 12 }}>
        <ChangeChip color="info" count={doc.steps.length} label="Étapes extraites" />
        <ChangeChip color="success" count={diff.added_steps.length} label="Nouvelles étapes" />
        <ChangeChip color="warn" count={diff.modified_steps.length} label="Étapes modifiées" />
        <ChangeChip color="error" count={diff.removed_steps.length} label="Étapes supprimées" />
      </div>

      <details open style={{ marginBottom: 12 }}>
        <summary style={{ cursor: "pointer", fontWeight: 600, marginBottom: 8 }}>
          Détail des étapes ({doc.steps.length})
        </summary>
        <div className="sa-table-wrap" style={{ marginTop: 8 }}>
          <table className="sa-table">
            <thead>
              <tr>
                <th style={{ width: 50 }}>#</th>
                <th>Code</th>
                <th>Type</th>
                <th>Libellé</th>
                <th>Question / Action</th>
                <th>Validation</th>
                <th>Suivant</th>
              </tr>
            </thead>
            <tbody>
              {doc.steps.map((s, i) => (
                <tr key={s.code}>
                  <td className="sa-mono">{i + 1}</td>
                  <td className="sa-mono">{s.code}</td>
                  <td>
                    <span className={`sa-badge ${typeBadge(s.type)}`}>{s.type}</span>
                  </td>
                  <td>{s.label}</td>
                  <td style={{ maxWidth: 320, whiteSpace: "normal" }}>
                    {s.question || (s.action_name ? <em>→ {s.action_name}</em> : "—")}
                  </td>
                  <td style={{ fontSize: 12 }}>{summarizeRules(s.validation_rules)}</td>
                  <td className="sa-mono" style={{ fontSize: 12 }}>
                    {s.next_step_code || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {Object.keys(doc.messages).length > 0 && (
        <details style={{ marginBottom: 12 }}>
          <summary style={{ cursor: "pointer", fontWeight: 600, marginBottom: 8 }}>
            Messages extraits ({Object.keys(doc.messages).length})
          </summary>
          <div style={{ marginTop: 8 }}>
            {Object.entries(doc.messages).map(([code, text]) => (
              <div
                key={code}
                style={{
                  padding: 8,
                  borderBottom: "1px solid rgb(var(--color-border-default) / 0.4)",
                }}
              >
                <div className="sa-mono" style={{ fontSize: 12, opacity: 0.7 }}>
                  {code}
                </div>
                <div style={{ marginTop: 4, whiteSpace: "pre-wrap" }}>{text}</div>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="sa-alert sa-alert--info" role="status" style={{ marginBottom: 12 }}>
        <Icon name="information-circle" className="i" />
        <div className="sa-alert__body">
          <p className="sa-alert__text">
            Vérifiez les types, validations et chaînages. Si quelque chose cloche, corrigez
            le document source et relancez.
          </p>
        </div>
      </div>

      <div className="sa-row" style={{ gap: 8, justifyContent: "flex-end" }}>
        <button
          type="button"
          className="sa-btn sa-btn--ghost"
          onClick={onCancel}
          disabled={applying}
        >
          Jeter
        </button>
        <button
          type="button"
          className="sa-btn sa-btn--primary"
          onClick={onApply}
          disabled={applying}
        >
          {applying ? "Application…" : "Appliquer et activer"}
        </button>
      </div>
    </>
  );
}

function typeBadge(type: string): string {
  switch (type) {
    case "message":
      return "sa-badge--info";
    case "question":
      return "sa-badge--ok";
    case "action":
      return "sa-badge--warn";
    case "decision":
      return "sa-badge--error";
    default:
      return "";
  }
}

function summarizeRules(rules: Record<string, any>): string {
  const forms = rules?.form_fields;
  if (Array.isArray(forms) && forms.length > 0) {
    const linked = forms.filter((f) => f.options_ref).length;
    const summary = forms
      .map((f) => (f.options_ref ? `${f.label || f.key} [${f.options_ref}]` : f.label || f.key))
      .slice(0, 4)
      .join(", ");
    const linkedHint = linked > 0 ? ` · ${linked} lié(s) à référentiel` : "";
    return `Form ${forms.length} champs${linkedHint} : ${summary}${forms.length > 4 ? "…" : ""}`;
  }
  if (rules?.options_ref) {
    return `Choix dans la liste « ${rules.options_ref} »`;
  }
  const list = rules?.rules;
  if (Array.isArray(list) && list.length > 0) {
    return list.map((r) => (r.value ? `${r.type}:${r.value}` : r.type)).join(" · ");
  }
  if (rules?.regex) return `regex:${rules.regex}`;
  if (rules?.format) return `format:${rules.format}`;
  return "—";
}
