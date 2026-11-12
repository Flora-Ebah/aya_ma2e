"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";
import ListPagination from "@/app/(app)/(workspace)/dossiers/_ListPagination";

/** Réponse de GET /api/collaborateurs/stats */
type RefStats = {
  total: number;
  actifs: number;
  par_employeur: { code: string; total: number }[];
  dernier_import: { date: string; fichier: string | null; lignes: number | null } | null;
  base_ma2e: { total: number; dernier_import: string | null };
};

/**
 * Référentiels fermés — listes de valeurs utilisées par les parcours IA.
 *
 * Quand l'IA extrait un parcours depuis un document, elle lie automatiquement
 * les champs énumérables (civilité, situation matrimoniale, type de pièce…)
 * à l'une de ces listes. Cette page permet à l'admin d'ajouter / éditer /
 * supprimer les listes et leurs items.
 *
 * Une entrée spéciale « Sociétaires » est ajoutée en haut de la table : elle
 * référence le fichier RH des agents du groupe (import CSV/XLSX) utilisé
 * pour la vérification matricule lors de l'inscription.
 */

type Item = { code?: string | null; label: string; synonyms?: string[] };

type RefList = {
  id: string;
  key: string;
  label: string;
  description: string | null;
  aliases: string[];
  items: Item[];
  is_system: boolean;
  allow_other: boolean;
  created_at: string;
  updated_at: string;
};

type Societaire = {
  id: string;
  matricule: string;
  employeur_code: string;
  nom: string;
  prenoms: string;
  email: string | null;
  telephone: string | null;
  fonction: string | null;
  statut: string;
};

type Employeur = { code: string; name: string };

const STATUT_LABELS: Record<string, string> = {
  actif: "Actif", retraite: "Retraité", demission: "Démission", licencie: "Licencié", inactif: "Inactif",
};
const HIST_PAGE_SIZE = 25;

/** Ligne de GET /api/collaborateurs/historique (textes déjà rédigés côté serveur) */
type HistoriqueItem = {
  id: string;
  date: string;
  type: string;
  libelle: string;
  detail: string;
  auteur: string;
};

const HIST_TYPES: Record<string, { label: string; badge: string }> = {
  import: { label: "Import", badge: "sa-badge--info" },
  import_refuse: { label: "Import refusé", badge: "sa-badge--error" },
  export: { label: "Export", badge: "sa-badge--neutral" },
  ajout: { label: "Ajout", badge: "sa-badge--ok" },
  modification: { label: "Modification", badge: "sa-badge--warn" },
  retrait: { label: "Retrait", badge: "sa-badge--error" },
};

export default function ListesPage() {
  const [lists, setLists] = useState<RefList[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<RefList | null>(null);
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);
  // Chiffres du référentiel ERANOVE ET de la base MA2E importée (ligne « Référentiel » ci-dessous)
  const [refStats, setRefStats] = useState<RefStats | null>(null);
  const [societairesOpen, setSocietairesOpen] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await api.listReferenceLists();
      setLists(data);
    } catch (e: any) {
      setErr(e?.message ?? "Erreur de chargement.");
    } finally {
      setLoading(false);
    }
  }, []);

  const reloadSocietairesCount = useCallback(async () => {
    try {
      setRefStats(await api.collaborateursStats());
    } catch {
      setRefStats(null);
    }
  }, []);

  useEffect(() => {
    reloadSocietairesCount();
  }, [reloadSocietairesCount]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  async function remove(l: RefList) {
    if (l.is_system) return;
    if (!confirm(`Supprimer définitivement la liste « ${l.label} » ?`)) return;
    try {
      await api.deleteReferenceList(l.id);
      setToast({ type: "success", text: "Liste supprimée." });
      reload();
    } catch (e: any) {
      setToast({ type: "error", text: e?.message ?? "Erreur." });
    }
  }

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <h1 className="sa-page-title">Listes de valeurs</h1>
          <p className="sa-page-desc">
            Références fermées utilisées par l&apos;IA pour détecter les champs énumérables
            (civilité, situation matrimoniale, type de pièce, catégorie…) et proposer
            automatiquement un choix numéroté dans le chat.
          </p>
        </div>
        <div className="sa-page-actions">
          <button
            type="button"
            className="sa-btn sa-btn--primary"
            onClick={() => setCreating(true)}
          >
            <Icon name="add-01" className="i" />
            Nouvelle liste
          </button>
        </div>
      </header>

      {err && (
        <div className="sa-alert sa-alert--error" role="alert">
          <Icon name="alert-circle" className="i" />
          <div className="sa-alert__body">
            <p className="sa-alert__text">{err}</p>
          </div>
        </div>
      )}

      <section className="sa-card" aria-label="Liste des référentiels">
        {loading ? (
          <div className="sa-skeleton sa-skeleton--text" style={{ width: 320 }} />
        ) : lists.length === 0 ? (
          <div className="sa-empty">
            <Icon name="list-view" className="i" />
            <div className="sa-empty__title">Aucune liste</div>
            <p className="sa-empty__text">Les listes système devraient apparaître au premier chargement.</p>
          </div>
        ) : (
          <div className="sa-table-wrap">
            <table className="sa-table">
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Clé technique</th>
                  <th>Valeurs</th>
                  <th>Autre libre</th>
                  <th style={{ width: 160 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {/* Entrée spéciale « Sociétaires » — alimentée par import CSV, pas une liste fermée classique */}
                <tr style={{ background: "rgb(var(--color-brand-primary) / 0.04)" }}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <strong>Référentiel des sociétaires ERANOVE</strong>
                      <span
                        className="sa-badge"
                        style={{
                          background: "rgb(var(--color-brand-primary) / 0.12)",
                          color: "rgb(var(--color-brand-primary))",
                          padding: "2px 8px",
                          fontSize: 11,
                          borderRadius: 4,
                          fontWeight: 500,
                        }}
                      >
                        Fichier RH
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 2 }}>
                      Liste des sociétaires du groupe ERANOVE — sert à vérifier qu&apos;un
                      candidat appartient bien au personnel.
                    </div>
                  </td>
                  <td>
                    <code style={{ fontSize: 12 }}>societaires</code>
                  </td>
                  <td>
                    {refStats == null ? (
                      <span style={{ fontSize: 13 }}>—</span>
                    ) : (
                      <>
                        <div style={{ fontSize: 13 }}>
                          <strong>Référentiel ERANOVE :</strong>{" "}
                          {refStats.total === 0 ? "aucun matricule chargé" : `${refStats.total.toLocaleString("fr-FR")} matricule${refStats.total > 1 ? "s" : ""}`}
                        </div>
                      </>
                    )}
                    <div style={{ fontSize: 11, color: "rgb(var(--color-text-muted))", marginTop: 2 }}>
                      Import CSV / XLSX (référentiel ou base MA2E)
                    </div>
                  </td>
                  <td>—</td>
                  <td>
                    <button
                      type="button"
                      className="sa-btn sa-btn--ghost sa-btn--sm"
                      onClick={() => setSocietairesOpen(true)}
                    >
                      <Icon name="edit-02" className="i" />
                      Gérer
                    </button>
                  </td>
                </tr>
                {lists.map((l) => (
                  <tr key={l.id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <strong>{l.label}</strong>
                        {l.is_system && (
                          <span
                            className="sa-badge"
                            style={{
                              background: "rgb(var(--color-brand-primary) / 0.12)",
                              color: "rgb(var(--color-brand-primary))",
                              padding: "2px 8px",
                              fontSize: 11,
                              borderRadius: 4,
                              fontWeight: 500,
                            }}
                          >
                            Système
                          </span>
                        )}
                      </div>
                      {l.description && (
                        <div style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 2 }}>
                          {l.description}
                        </div>
                      )}
                    </td>
                    <td>
                      <code style={{ fontSize: 12 }}>{l.key}</code>
                    </td>
                    <td>
                      <span style={{ fontSize: 13 }}>
                        {(l.items || []).slice(0, 4).map((it) => it.label).join(" · ")}
                        {l.items.length > 4 ? ` + ${l.items.length - 4}` : ""}
                      </span>
                      <div style={{ fontSize: 11, color: "rgb(var(--color-text-muted))", marginTop: 2 }}>
                        {l.items.length} item(s)
                      </div>
                    </td>
                    <td>{l.allow_other ? "Oui" : "Non"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          type="button"
                          className="sa-btn sa-btn--ghost sa-btn--sm"
                          onClick={() => setEditing(l)}
                        >
                          <Icon name="edit-02" className="i" />
                          Éditer
                        </button>
                        {!l.is_system && (
                          <button
                            type="button"
                            className="sa-btn sa-btn--ghost sa-btn--sm"
                            onClick={() => remove(l)}
                            aria-label="Supprimer"
                          >
                            <Icon name="delete-02" className="i" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {societairesOpen && (
        <SocietairesModal
          onClose={() => setSocietairesOpen(false)}
          onChanged={() => reloadSocietairesCount()}
          notify={(msg, type) => setToast({ type, text: msg })}
        />
      )}

      {(editing || creating) && (
        <EditorModal
          initial={editing}
          onClose={() => {
            setEditing(null);
            setCreating(false);
          }}
          onSaved={(msg) => {
            setToast({ type: "success", text: msg });
            setEditing(null);
            setCreating(false);
            reload();
          }}
          onError={(msg) => setToast({ type: "error", text: msg })}
        />
      )}

      {toast && <TopToast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}

// -----------------------------------------------------------------------------
// EditorModal — création ou édition
// -----------------------------------------------------------------------------

function EditorModal({
  initial,
  onClose,
  onSaved,
  onError,
}: {
  initial: RefList | null;
  onClose: () => void;
  onSaved: (msg: string) => void;
  onError: (msg: string) => void;
}) {
  const isEdit = !!initial;
  const [label, setLabel] = useState(initial?.label ?? "");
  const [key, setKey] = useState(initial?.key ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [aliases, setAliases] = useState<string>((initial?.aliases ?? []).join(", "));
  const [allowOther, setAllowOther] = useState<boolean>(initial?.allow_other ?? false);
  const [items, setItems] = useState<Item[]>(initial?.items ?? [{ label: "", synonyms: [] }]);
  const [saving, setSaving] = useState(false);
  const firstInputRef = useRef<HTMLInputElement | null>(null);

  // Liste « Employeurs du groupe » : chaque employeur porte aussi son format de matricule
  const isEmployeurs = initial?.key === "employeurs";
  const [emps, setEmps] = useState<EmployeurFormat[]>([]);
  const [fmts, setFmts] = useState<Record<string, { fmt: string; ex: string; test: string }>>({});
  useEffect(() => {
    if (!isEmployeurs) return;
    api.listEmployeurs(true).then((data: EmployeurFormat[]) => {
      setEmps(data);
      setFmts(Object.fromEntries(data.map((e) => [e.code.toUpperCase(), { fmt: e.matricule_format ?? "", ex: e.matricule_exemple ?? "", test: "" }])));
    }).catch(() => {});
  }, [isEmployeurs]);
  const empOf = (it: Item) => emps.find((e) => e.code.toUpperCase() === (it.code || it.label || "").trim().toUpperCase());

  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  function setItem(i: number, patch: Partial<Item>) {
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  }
  function addItem() {
    setItems((prev) => [...prev, { label: "", synonyms: [] }]);
  }
  function removeItem(i: number) {
    setItems((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function save() {
    const cleanedItems = items
      .map((it) => ({
        code: it.code || undefined,
        label: (it.label || "").trim(),
        synonyms: (it.synonyms || []).filter((s) => s.trim().length > 0),
      }))
      .filter((it) => it.label);

    if (!label.trim()) return onError("Le nom de la liste est obligatoire.");
    if (cleanedItems.length === 0) return onError("Ajoutez au moins un item.");
    if (!isEdit && !key.trim()) return onError("La clé technique est obligatoire.");

    const parsedAliases = aliases
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    setSaving(true);
    try {
      if (isEmployeurs) {
        for (const e of emps) {
          const d = fmts[e.code.toUpperCase()];
          if (!d) continue;
          if (d.fmt.trim() === (e.matricule_format ?? "") && d.ex.trim() === (e.matricule_exemple ?? "")) continue;
          try {
            await api.updateEmployeur(e.id, { matricule_format: d.fmt.trim(), matricule_exemple: d.ex.trim() });
          } catch (err: any) {
            throw new Error(`${e.code} : ${(err?.message ?? "format refusé").replace(/^\d+:\s*/, "")}`);
          }
        }
      }
      if (isEdit && initial) {
        await api.updateReferenceList(initial.id, {
          label: label.trim(),
          description: description.trim() || null,
          aliases: parsedAliases,
          items: cleanedItems,
          allow_other: allowOther,
        });
        onSaved("Liste mise à jour.");
      } else {
        await api.createReferenceList({
          key: key.trim(),
          label: label.trim(),
          description: description.trim() || undefined,
          aliases: parsedAliases,
          items: cleanedItems,
          allow_other: allowOther,
        });
        onSaved("Liste créée.");
      }
    } catch (e: any) {
      onError(e?.message?.replace(/^\d+:\s*/, "") ?? "Erreur.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        zIndex: 1000,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 24,
        overflowY: "auto",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="sa-card"
        style={{ maxWidth: 720, width: "100%", margin: "32px auto" }}
      >
        <div className="sa-card__header">
          <h2 className="sa-card__title">
            {isEdit ? `Éditer « ${initial?.label} »` : "Nouvelle liste de valeurs"}
          </h2>
          {initial?.is_system && (
            <p className="sa-card__desc">
              Liste système — vous pouvez éditer les items et alias, mais pas la supprimer.
            </p>
          )}
        </div>

        <div style={{ display: "grid", gap: 16, padding: "0 4px" }}>
          <div className="sa-form-row">
            <label className="sa-form-label">Nom de la liste</label>
            <input
              ref={firstInputRef}
              type="text"
              className="sa-input"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="ex : Catégories professionnelles"
            />
          </div>

          {!isEdit && (
            <div className="sa-form-row">
              <label className="sa-form-label">Clé technique (snake_case)</label>
              <input
                type="text"
                className="sa-input"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="ex : categories_professionnelles"
              />
              <div style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 4 }}>
                Non modifiable après création. Utilisé par le LLM pour détecter cette liste.
              </div>
            </div>
          )}

          <div className="sa-form-row">
            <label className="sa-form-label">Description (optionnel)</label>
            <input
              type="text"
              className="sa-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="ex : Catégorie du personnel du groupe ERANOVE"
            />
          </div>

          <div className="sa-form-row">
            <label className="sa-form-label">Mots déclencheurs (séparés par des virgules)</label>
            <input
              type="text"
              className="sa-input"
              value={aliases}
              onChange={(e) => setAliases(e.target.value)}
              placeholder="ex : catégorie, grade, échelon"
            />
            <div style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 4 }}>
              Aident l&apos;IA à matcher cette liste contre les libellés de champs du document.
            </div>
          </div>

          <div className="sa-form-row">
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={allowOther}
                onChange={(e) => setAllowOther(e.target.checked)}
              />
              <span>Autoriser une saisie libre en plus des choix (« Autre »)</span>
            </label>
          </div>

          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <label className="sa-form-label" style={{ margin: 0 }}>
                Items ({items.length})
              </label>
              <button
                type="button"
                className="sa-btn sa-btn--ghost sa-btn--sm"
                onClick={addItem}
              >
                <Icon name="add-01" className="i" />
                Ajouter
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {items.map((it, idx) => (
                <div key={idx} style={{ display: "grid", gap: 6 }}>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr auto",
                    gap: 8,
                    alignItems: "center",
                  }}
                >
                  <input
                    type="text"
                    className="sa-input"
                    placeholder={`Libellé ${idx + 1}`}
                    value={it.label}
                    onChange={(e) => setItem(idx, { label: e.target.value })}
                  />
                  <input
                    type="text"
                    className="sa-input"
                    placeholder="Synonymes (séparés par virgules)"
                    value={(it.synonyms || []).join(", ")}
                    onChange={(e) =>
                      setItem(idx, {
                        synonyms: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                  <button
                    type="button"
                    className="sa-btn sa-btn--ghost sa-btn--sm"
                    onClick={() => removeItem(idx)}
                    aria-label="Retirer cet item"
                    disabled={items.length === 1}
                  >
                    <Icon name="delete-02" className="i" />
                  </button>
                </div>
                {isEmployeurs && (() => {
                  const e = empOf(it);
                  if (!e) return null;
                  const k = e.code.toUpperCase();
                  const d = fmts[k] ?? { fmt: "", ex: "", test: "" };
                  const set = (patch: Partial<typeof d>) => setFmts((p) => ({ ...p, [k]: { ...d, ...patch } }));
                  const res = testFormat(d.fmt, d.test);
                  return (
                    <div style={{ display: "grid", gridTemplateColumns: "1.4fr 0.8fr 1fr", gap: 8, paddingLeft: 12,
                      borderLeft: "2px solid rgb(var(--color-border-default))" }}>
                      <input className="sa-input" value={d.fmt} maxLength={120} style={{ fontFamily: "monospace" }}
                        placeholder="Format du matricule (ex. [A-Z]\d{4}) — vide = aucun contrôle"
                        aria-label={`Format du matricule ${e.code}`} onChange={(ev) => set({ fmt: ev.target.value })} />
                      <input className="sa-input" value={d.ex} maxLength={64} placeholder="Exemple (A1234)"
                        aria-label={`Exemple de matricule ${e.code}`} onChange={(ev) => set({ ex: ev.target.value })} />
                      <div>
                        <input className="sa-input" value={d.test} placeholder="Tester un matricule"
                          aria-label={`Tester un matricule ${e.code}`} onChange={(ev) => set({ test: ev.target.value })} />
                        {res !== null && (
                          <div style={{ fontSize: 12, marginTop: 2, color: res ? "rgb(var(--color-status-success))" : "rgb(var(--color-status-error))" }}>
                            {res ? "✓ Valide" : "✗ Ne respecte pas le format"}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
                </div>
              ))}
            </div>
            {isEmployeurs && (
              <div style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 8 }}>
                Le format est une expression régulière appliquée au matricule en majuscules, sans espace ni tiret
                (ex. <code>{"[A-Z]\\d{4}"}</code> = 1 lettre + 4 chiffres, <code>{"\\d{5,8}"}</code> = 5 à 8 chiffres). Il est contrôlé à
                l&apos;inscription, à l&apos;ajout et à l&apos;import du référentiel.
              </div>
            )}
          </div>
        </div>

        <div
          className="sa-card__footer"
          style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 24 }}
        >
          <button
            type="button"
            className="sa-btn sa-btn--ghost"
            onClick={onClose}
            disabled={saving}
          >
            Annuler
          </button>
          <button
            type="button"
            className="sa-btn sa-btn--primary"
            onClick={save}
            disabled={saving}
          >
            {saving ? "Enregistrement…" : isEdit ? "Enregistrer" : "Créer la liste"}
          </button>
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Règle « matricule à format variable » : un format par employeur, édité dans la liste « Employeurs du groupe ».
// Le format est une expression régulière appliquée au matricule normalisé (majuscules, sans espace ni tiret).
// -----------------------------------------------------------------------------

type EmployeurFormat = { id: string; code: string; name: string; matricule_format?: string | null; matricule_exemple?: string | null };

function testFormat(pattern: string, value: string): boolean | null {
  if (!pattern.trim() || !value.trim()) return null;
  try {
    const norm = value.toUpperCase().replace(/[\s\-_./]/g, "");
    return new RegExp(`^(?:${pattern.trim()})$`, "i").test(norm);
  } catch {
    return null;
  }
}

// -----------------------------------------------------------------------------
// SocietairesModal — gestion inline des sociétaires (fichier RH).
// -----------------------------------------------------------------------------

function SocietairesModal({
  onClose,
  onChanged,
  notify,
}: {
  onClose: () => void;
  onChanged: () => void;
  notify: (msg: string, type: "success" | "error") => void;
}) {
  const [employeurs, setEmployeurs] = useState<Employeur[]>([]);
  // Historique : liste paginée des actions faites dans le référentiel (ajouts, modifications, retraits, imports, exports)
  const [histItems, setHistItems] = useState<HistoriqueItem[]>([]);
  const [histTotal, setHistTotal] = useState(0);
  const [histPage, setHistPage] = useState(1);
  const [histLoading, setHistLoading] = useState(false);
  const [histVersion, setHistVersion] = useState(0); // incrémenté après chaque action pour recharger l'historique
  const bumpHistory = () => setHistVersion((v) => v + 1);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    setHistLoading(true);
    api.historiqueCollaborateurs({ page: histPage, page_size: HIST_PAGE_SIZE })
      .then((d: any) => { if (alive) { setHistItems(d.items); setHistTotal(d.total); } })
      .catch((e: any) => notify(e?.message ?? "Erreur de chargement de l'historique.", "error"))
      .finally(() => { if (alive) setHistLoading(false); });
    return () => { alive = false; };
  }, [histPage, histVersion, notify]);

  useEffect(() => {
    api.listEmployeurs(false).then(setEmployeurs).catch(() => {});
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        zIndex: 1100,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 24,
        overflowY: "auto",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="sa-card"
        style={{ maxWidth: 960, width: "100%", margin: "32px auto" }}
      >
        <div
          className="sa-card__header"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}
        >
          <div>
            <h2 className="sa-card__title">Référentiel des sociétaires ERANOVE</h2>
            <p className="sa-card__desc">
              Liste des agents du groupe éligibles à MA2E, utilisée pour vérifier un matricule
              lors de l&apos;inscription.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              className="sa-btn sa-btn--secondary"
              onClick={() => setImportOpen(true)}
            >
              <Icon name="upload-02" className="i" />
              Importer un fichier
            </button>
            <button
              type="button"
              className="sa-btn sa-btn--primary"
              onClick={() => setAddOpen(true)}
            >
              <Icon name="add-01" className="i" />
              Ajouter
            </button>
          </div>
        </div>

        <>
          <div className="sa-pagination__info" style={{ paddingBottom: 8 }} aria-live="polite">
            {histLoading ? "Chargement…" : `${histTotal.toLocaleString("fr-FR")} action${histTotal > 1 ? "s" : ""} enregistrée${histTotal > 1 ? "s" : ""}`}
          </div>
          {!histLoading && histItems.length === 0 ? (
            <div className="sa-empty">
              <Icon name="list-view" className="i" />
              <div className="sa-empty__title">Aucune action enregistrée</div>
              <p className="sa-empty__text">Les imports, exports, ajouts, modifications et retraits apparaîtront ici.</p>
            </div>
          ) : (
            <div className="sa-table-wrap" style={{ maxHeight: 460, overflowY: "auto" }}>
              <table className="sa-table" aria-busy={histLoading}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Action</th>
                    <th>Détail</th>
                    <th>Par</th>
                  </tr>
                </thead>
                <tbody>
                  {histItems.map((h) => {
                    const t = HIST_TYPES[h.type] ?? { label: h.type, badge: "sa-badge--neutral" };
                    return (
                      <tr key={h.id}>
                        <td style={{ whiteSpace: "nowrap" }}>
                          {new Date(h.date).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}
                        </td>
                        <td>
                          <span className={`sa-badge ${t.badge}`}>{t.label}</span>
                          <div style={{ marginTop: 4 }}>{h.libelle}</div>
                        </td>
                        <td style={{ fontSize: 13 }}>{h.detail || "—"}</td>
                        <td style={{ whiteSpace: "nowrap" }}>{h.auteur}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <ListPagination page={histPage} pageSize={HIST_PAGE_SIZE} total={histTotal} onPageChange={setHistPage} />
          <p style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 12 }}>
            Les imports et les exports sont enregistrés depuis le début ; les ajouts, modifications et retraits
            unitaires le sont depuis la mise en place de cet historique. Seuls le matricule et les champs modifiés
            sont conservés, jamais les noms ni les coordonnées.
          </p>
        </>

        <div
          className="sa-card__footer"
          style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}
        >
          <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>
            Fermer
          </button>
        </div>
      </div>

      {addOpen && (
        <AddSocietaireModal
          employeurs={employeurs}
          onClose={() => setAddOpen(false)}
          onDone={async () => {
            setAddOpen(false);
            bumpHistory();
            onChanged();
          }}
          notify={notify}
        />
      )}
      {importOpen && (
        <ImportSocietairesModal
          onClose={() => setImportOpen(false)}
          onDone={async () => {
            setImportOpen(false);
            bumpHistory();
            onChanged();
          }}
          notify={notify}
        />
      )}
    </div>
  );
}

function AddSocietaireModal({
  employeurs,
  initial,
  onClose,
  onDone,
  notify,
}: {
  employeurs: Employeur[];
  /** Renseigné = mode « modification » : matricule et employeur sont verrouillés (l'API ne les modifie pas) */
  initial?: Societaire;
  onClose: () => void;
  onDone: () => void;
  notify: (msg: string, type: "success" | "error") => void;
}) {
  const edit = !!initial;
  const [matricule, setMatricule] = useState(initial?.matricule ?? "");
  const [employeurCode, setEmployeurCode] = useState(initial?.employeur_code ?? employeurs[0]?.code ?? "");
  const [nom, setNom] = useState(initial?.nom ?? "");
  const [prenoms, setPrenoms] = useState(initial?.prenoms ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [telephone, setTelephone] = useState(initial?.telephone ?? "");
  const [fonction, setFonction] = useState(initial?.fonction ?? "");
  const [statut, setStatut] = useState(initial?.statut ?? "actif");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (initial) {
        await api.updateCollaborateur(initial.id, {
          nom: nom.trim(),
          prenoms: prenoms.trim(),
          email: email.trim() || null,
          telephone: telephone.trim() || null,
          fonction: fonction.trim() || null,
          statut,
        });
        notify("Matricule modifié.", "success");
      } else {
        await api.createCollaborateur({
          matricule: matricule.trim().toUpperCase(),
          employeur_code: employeurCode,
          nom: nom.trim(),
          prenoms: prenoms.trim(),
          email: email.trim() || null,
          telephone: telephone.trim() || null,
          fonction: fonction.trim() || null,
          statut,
        });
        notify("Sociétaire ajouté.", "success");
      }
      onDone();
    } catch (e: any) {
      notify(e?.message?.replace(/^\d+:\s*/, "") ?? "Erreur.", "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        zIndex: 1200,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 24,
        overflowY: "auto",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="sa-card"
        style={{ maxWidth: 560, width: "100%", margin: "32px auto" }}
      >
        <div className="sa-card__header">
          <h2 className="sa-card__title">{edit ? `Modifier le matricule ${initial!.matricule}` : "Ajouter un sociétaire"}</h2>
          {edit && (
            <p className="sa-card__desc">Le matricule et l&apos;employeur ne sont pas modifiables : retirez la ligne puis ajoutez-la de nouveau.</p>
          )}
        </div>
        <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label className="sa-form-label">Matricule</label>
              <input
                className="sa-input"
                required
                disabled={edit}
                value={matricule}
                onChange={(e) => setMatricule(e.target.value)}
              />
            </div>
            <div>
              <label className="sa-form-label">Employeur</label>
              <select
                className="sa-input"
                value={employeurCode}
                onChange={(e) => setEmployeurCode(e.target.value)}
                required
                disabled={edit}
              >
                {/* en modification, l'employeur d'origine reste affiché même s'il n'est plus dans la liste active */}
                {edit && !employeurs.some((e) => e.code === employeurCode) && <option value={employeurCode}>{employeurCode}</option>}
                {employeurs.map((e) => (
                  <option key={e.code} value={e.code}>
                    {e.code} — {e.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label className="sa-form-label">Nom</label>
              <input
                className="sa-input"
                required
                value={nom}
                onChange={(e) => setNom(e.target.value)}
              />
            </div>
            <div>
              <label className="sa-form-label">Prénoms</label>
              <input
                className="sa-input"
                required
                value={prenoms}
                onChange={(e) => setPrenoms(e.target.value)}
              />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label className="sa-form-label">Email (optionnel)</label>
              <input
                className="sa-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="sa-form-label">Téléphone (optionnel)</label>
              <input
                className="sa-input"
                value={telephone}
                onChange={(e) => setTelephone(e.target.value)}
              />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label className="sa-form-label">Fonction (optionnel)</label>
              <input
                className="sa-input"
                value={fonction}
                onChange={(e) => setFonction(e.target.value)}
              />
            </div>
            <div>
              <label className="sa-form-label">Statut</label>
              <select className="sa-input" value={statut} onChange={(e) => setStatut(e.target.value)}>
                {Object.entries(STATUT_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
            </div>
          </div>
          <div
            style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}
          >
            <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" className="sa-btn sa-btn--primary" disabled={submitting}>
              {submitting ? "Enregistrement…" : edit ? "Enregistrer" : "Ajouter"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

type ImportKind = "base" | "referentiel";

type ImportReportData = {
  total_lines: number;
  accepted: number;
  updated?: number;
  rejected: number;
  dry_run?: boolean;
  errors: Array<{ line: number; error: string; data: any }>;
  warnings?: Array<{ line: number; id_client?: string; warning: string }>;
};

// Deux fichiers différents passent par cette fenêtre :
// - « base »        → base des sociétaires MA2E (fichier source Perfect Vision : id_client,
//                     num_manuel, nom_client…) → POST /api/imports/societaires. Analyse
//                     (dry_run) puis confirmation ; ré-import = mise à jour, sans doublon.
// - « referentiel » → référentiel des sociétaires ERANOVE (matricule, employeur_code, nom…)
//                     → POST /api/imports/collaborateurs, transaction atomique.
const IMPORT_KINDS: Record<ImportKind, { target: string; title: string; desc: string }> = {
  base: {
    target: "societaires",
    title: "Base des sociétaires MA2E",
    desc: "Fichier source MA2E (id_client, num_manuel, nom_client…). Analyse puis confirmation ; un ré-import met à jour sans doublon.",
  },
  referentiel: {
    target: "collaborateurs",
    title: "Référentiel des sociétaires ERANOVE",
    desc: "Liste des agents éligibles (matricule, employeur_code, nom, prenoms). Aucune ligne n'est insérée si une seule contient une erreur.",
  },
};

function ImportSocietairesModal({
  onClose,
  onDone,
  notify,
}: {
  onClose: () => void;
  onDone: () => void;
  notify: (msg: string, type: "success" | "error") => void;
}) {
  const [kind, setKind] = useState<ImportKind>("base");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState<ImportReportData | null>(null);
  const isBase = kind === "base";
  const target = IMPORT_KINDS[kind].target;

  async function run(dryRun: boolean) {
    if (!file) return;
    setUploading(true);
    try {
      const r: ImportReportData = await api.uploadImport(target, file, { dryRun });
      setReport(r);
      if (isBase) {
        if (dryRun) return; // l'aperçu s'affiche, l'utilisateur confirme ensuite
        notify(
          `Base MA2E : ${r.accepted} créé(s), ${r.updated ?? 0} mis à jour` +
            (r.rejected ? `, ${r.rejected} ligne(s) rejetée(s).` : "."),
          r.rejected ? "error" : "success",
        );
      } else if (r.rejected > 0) {
        notify(`Import refusé : ${r.rejected} erreur(s) — aucune ligne insérée.`, "error");
      } else {
        notify(`${r.accepted} matricule(s) importé(s).`, "success");
      }
    } catch (e: any) {
      notify(e?.message ?? "Erreur.", "error");
    } finally {
      setUploading(false);
    }
  }

  function reset() {
    setReport(null);
    setFile(null);
  }

  const isPreview = !!report?.dry_run;
  const written = isBase ? report && !report.dry_run : report && report.rejected === 0;
  // Fichier source MA2E déposé dans le référentiel ERANOVE : toutes les lignes manquent de `matricule`.
  const looksLikeMa2eSource =
    !isBase &&
    !!report &&
    report.accepted === 0 &&
    report.errors.length > 0 &&
    report.errors.every((e) => e.error.includes("'matricule'"));

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        zIndex: 1200,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 24,
        overflowY: "auto",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !uploading) onClose();
      }}
    >
      <div className="sa-card" style={{ maxWidth: 760, width: "100%", margin: "32px auto" }}>
        <div className="sa-card__header">
          <h2 className="sa-card__title">Importer un fichier</h2>
          <p className="sa-card__desc">CSV (UTF-8 ou Windows) ou Excel (.xlsx).</p>
        </div>

        {!report && (
          <div style={{ display: "grid", gap: 12 }}>
            <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
              <legend className="sa-label" style={{ marginBottom: 6 }}>
                Type de fichier
              </legend>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(Object.keys(IMPORT_KINDS) as ImportKind[]).map((k) => (
                  <label key={k} className="sa-choice">
                    <input
                      type="radio"
                      name="import-kind"
                      checked={kind === k}
                      onChange={() => setKind(k)}
                    />
                    <span className="sa-choice__body">
                      <span className="sa-choice__title">{IMPORT_KINDS[k].title}</span>
                      <span className="sa-choice__desc">{IMPORT_KINDS[k].desc}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div>
              <a
                href={api.downloadImportTemplate(target)}
                className="sa-btn sa-btn--ghost sa-btn--sm"
                download
              >
                <Icon name="download-02" className="i" />
                {isBase ? "Télécharger les en-têtes attendus" : "Télécharger le modèle CSV"}
              </a>
            </div>
            <label
              style={{
                border: "2px dashed rgb(var(--color-border-default, 200 200 200))",
                borderRadius: 8,
                padding: 24,
                textAlign: "center",
                cursor: "pointer",
                display: "block",
              }}
            >
              <input
                type="file"
                accept=".csv,.xlsx,text/csv"
                style={{ display: "none" }}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <Icon name="upload-02" className="i" />
              <div style={{ marginTop: 8 }}>
                {file ? file.name : "Déposez votre fichier ici ou cliquez pour parcourir"}
              </div>
              {file && (
                <div style={{ fontSize: 12, color: "rgb(var(--color-text-muted))", marginTop: 4 }}>
                  {(file.size / 1024).toFixed(1)} Ko
                </div>
              )}
            </label>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>
                Annuler
              </button>
              <button
                type="button"
                className="sa-btn sa-btn--primary"
                onClick={() => run(isBase)}
                disabled={!file || uploading}
              >
                {uploading
                  ? isBase
                    ? "Analyse en cours…"
                    : "Import en cours…"
                  : isBase
                    ? "Analyser le fichier"
                    : "Lancer l'import"}
              </button>
            </div>
          </div>
        )}

        {report && (
          <div style={{ display: "grid", gap: 12 }}>
            {isPreview && (
              <div className="sa-alert sa-alert--info" role="status" style={{ padding: 12 }}>
                <Icon name="information-circle" className="i" />
                <span>
                  Aperçu : rien n&apos;a encore été enregistré. Vérifiez les chiffres, puis
                  confirmez l&apos;import.
                </span>
              </div>
            )}
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <Metric label="Total" value={report.total_lines} />
              <Metric
                label={isBase ? (isPreview ? "À créer" : "Créés") : "Acceptées"}
                value={report.accepted}
                color="rgb(var(--color-brand-primary))"
              />
              {isBase && (
                <Metric
                  label={isPreview ? "À mettre à jour" : "Mis à jour"}
                  value={report.updated ?? 0}
                  color="rgb(var(--color-brand-primary))"
                />
              )}
              <Metric
                label="Rejetées"
                value={report.rejected}
                color={
                  report.rejected > 0
                    ? "rgb(var(--color-feedback-error))"
                    : "rgb(var(--color-brand-primary))"
                }
              />
              {isBase && (report.warnings?.length ?? 0) > 0 && (
                <Metric label="À vérifier" value={report.warnings!.length} />
              )}
            </div>

            {looksLikeMa2eSource && (
              <div className="sa-alert sa-alert--warning" role="alert" style={{ padding: 12 }}>
                <Icon name="alert-02" className="i" />
                <span>
                  Ce fichier ressemble au fichier source MA2E (pas de colonne « matricule »).
                  Choisissez plutôt « {IMPORT_KINDS.base.title} ».
                </span>
                <button
                  type="button"
                  className="sa-btn sa-btn--secondary sa-btn--sm"
                  style={{ marginLeft: "auto" }}
                  onClick={() => {
                    setKind("base");
                    setReport(null);
                  }}
                >
                  Importer comme base MA2E
                </button>
              </div>
            )}

            {(report.errors.length > 0 || (report.warnings?.length ?? 0) > 0) && (
              <div
                style={{
                  maxHeight: 260,
                  overflowY: "auto",
                  border: "1px solid rgb(var(--color-border-default, 230 230 230))",
                  borderRadius: 6,
                }}
              >
                <table className="sa-table">
                  <thead>
                    <tr>
                      <th style={{ width: 60 }}>Ligne</th>
                      <th style={{ width: 110 }}>Type</th>
                      <th>Détail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.errors.map((e, i) => (
                      <tr key={`e${i}`}>
                        <td style={{ fontFamily: "monospace" }}>{e.line}</td>
                        <td style={{ color: "rgb(var(--color-feedback-error))" }}>Rejetée</td>
                        <td>{e.error}</td>
                      </tr>
                    ))}
                    {(report.warnings ?? []).map((w, i) => (
                      <tr key={`w${i}`}>
                        <td style={{ fontFamily: "monospace" }}>{w.line}</td>
                        <td>À vérifier</td>
                        <td>
                          {w.id_client ? `${w.id_client} — ` : ""}
                          {w.warning}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {written && report.errors.length === 0 && (
              <div className="sa-alert sa-alert--success" role="status" style={{ padding: 12 }}>
                <Icon name="checkmark-circle-02" className="i" />
                <span>
                  {isBase
                    ? `${report.accepted} sociétaire(s) créé(s) et ${report.updated ?? 0} mis à jour dans la base MA2E : ils apparaissent dans « Dossiers » (étiquette « Base MA2E ») et servent aux parcours « Consulter mon dossier » et « Modifier mes informations ».`
                    : `${report.accepted} matricule(s) importé(s) avec succès.`}
                </span>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" className="sa-btn sa-btn--ghost" onClick={reset}>
                {isPreview ? "Changer de fichier" : "Nouvel import"}
              </button>
              {isPreview ? (
                <button
                  type="button"
                  className="sa-btn sa-btn--primary"
                  onClick={() => run(false)}
                  disabled={uploading || report.accepted + (report.updated ?? 0) === 0}
                >
                  {uploading
                    ? "Import en cours…"
                    : `Confirmer l'import (${report.accepted + (report.updated ?? 0)} ligne(s))`}
                </button>
              ) : isBase && written ? (
                // Les sociétaires importés apparaissent dans la page « Dossiers » (et non dans
                // « Sociétaires éligibles », qui liste le référentiel ERANOVE) : on y mène.
                <>
                  <button type="button" className="sa-btn sa-btn--ghost" onClick={onDone}>
                    Fermer
                  </button>
                  <Link href="/dossiers?origine=import" className="sa-btn sa-btn--primary">
                    <Icon name="user-group" className="i" />
                    Voir les dossiers importés
                  </Link>
                </>
              ) : (
                <button
                  type="button"
                  className="sa-btn sa-btn--primary"
                  onClick={() => (written ? onDone() : onClose())}
                >
                  {written ? "Terminer" : "Fermer"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 110,
        padding: 12,
        // `--color-bg-elevated` n'existe pas dans tokens.css : le repli gris clair
        // s'appliquait aussi en thème sombre (chiffres blancs illisibles).
        background: "rgb(var(--color-bg-surface-subtle, 245 245 245))",
        borderRadius: 6,
      }}
    >
      <div style={{ fontSize: 11, color: "rgb(var(--color-text-muted))" }}>{label}</div>
      <div
        style={{
          fontSize: 22,
          fontWeight: 600,
          color: color ?? "rgb(var(--color-text-primary))",
        }}
      >
        {value}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// TopToast — même style que la page parcours
// -----------------------------------------------------------------------------

function TopToast({
  type,
  text,
  onClose,
}: {
  type: "success" | "error";
  text: string;
  onClose: () => void;
}) {
  const borderColor =
    type === "success"
      ? "rgb(var(--color-brand-primary))"
      : "rgb(var(--color-feedback-error))";
  return (
    <div
      style={{
        position: "fixed",
        top: 16,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        zIndex: 2000,
        pointerEvents: "none",
      }}
    >
      <div
        role="status"
        onClick={onClose}
        style={{
          pointerEvents: "auto",
          background: "rgb(var(--color-bg-surface))",
          color: "rgb(var(--color-text-primary))",
          border: `2px solid ${borderColor}`,
          padding: "10px 20px",
          borderRadius: 6,
          boxShadow: "0 4px 16px rgba(0,0,0,0.1)",
          fontWeight: 500,
          fontSize: 14,
          maxWidth: 520,
          cursor: "pointer",
        }}
      >
        {text}
      </div>
    </div>
  );
}
