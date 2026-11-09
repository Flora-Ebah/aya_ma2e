"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";

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

export default function ListesPage() {
  const [lists, setLists] = useState<RefList[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<RefList | null>(null);
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [societairesCount, setSocietairesCount] = useState<number | null>(null);
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
      const rows = await api.listCollaborateurs({ limit: 1000 });
      setSocietairesCount(rows.length);
    } catch {
      setSocietairesCount(null);
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
                      <strong>Sociétaires éligibles</strong>
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
                      Référentiel des matricules du groupe ERANOVE — sert à vérifier qu&apos;un
                      candidat appartient bien au personnel.
                    </div>
                  </td>
                  <td>
                    <code style={{ fontSize: 12 }}>societaires</code>
                  </td>
                  <td>
                    <span style={{ fontSize: 13 }}>
                      {societairesCount == null
                        ? "—"
                        : societairesCount === 0
                          ? "Aucun fichier importé"
                          : `${societairesCount} matricule(s) chargé(s)`}
                    </span>
                    <div style={{ fontSize: 11, color: "rgb(var(--color-text-muted))", marginTop: 2 }}>
                      Import CSV / XLSX
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
                <div
                  key={idx}
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
              ))}
            </div>
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
  const [rows, setRows] = useState<Societaire[]>([]);
  const [employeurs, setEmployeurs] = useState<Employeur[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listCollaborateurs({
        search: search || undefined,
        limit: 500,
      });
      setRows(data);
    } catch (e: any) {
      notify(e?.message ?? "Erreur de chargement.", "error");
    } finally {
      setLoading(false);
    }
  }, [search, notify]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api.listEmployeurs(false).then(setEmployeurs).catch(() => {});
  }, []);

  async function del(c: Societaire) {
    if (!confirm(`Retirer ${c.prenoms} ${c.nom} (${c.matricule}) du fichier ?`)) return;
    try {
      await api.deleteCollaborateur(c.id);
      notify("Sociétaire retiré.", "success");
      await load();
      onChanged();
    } catch (e: any) {
      notify(e?.message ?? "Erreur.", "error");
    }
  }

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
            <h2 className="sa-card__title">Sociétaires éligibles</h2>
            <p className="sa-card__desc">
              Fichier des matricules du groupe utilisé pour vérifier qu&apos;un candidat
              appartient bien au personnel ERANOVE.
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

        <div style={{ padding: "12px 0" }}>
          <input
            type="search"
            className="sa-input"
            placeholder="Rechercher par matricule, nom, email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {loading ? (
          <div style={{ padding: 24 }}>
            <div className="sa-skeleton sa-skeleton--text" style={{ width: 320 }} />
          </div>
        ) : rows.length === 0 ? (
          <div className="sa-empty">
            <Icon name="user-group" className="i" />
            <div className="sa-empty__title">Aucun sociétaire</div>
            <p className="sa-empty__text">
              Importez un CSV depuis le SI RH ou ajoutez un matricule manuellement.
            </p>
          </div>
        ) : (
          <div className="sa-table-wrap" style={{ maxHeight: 400, overflowY: "auto" }}>
            <table className="sa-table">
              <thead>
                <tr>
                  <th>Matricule</th>
                  <th>Nom / Prénoms</th>
                  <th>Employeur</th>
                  <th>Fonction</th>
                  <th>Statut</th>
                  <th style={{ width: 60 }}></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontFamily: "monospace", whiteSpace: "nowrap" }}>
                      {c.matricule}
                    </td>
                    <td>
                      <div>
                        {c.nom} {c.prenoms}
                      </div>
                      {c.email && (
                        <div
                          style={{
                            fontSize: 11,
                            color: "rgb(var(--color-text-muted))",
                          }}
                        >
                          {c.email}
                        </div>
                      )}
                    </td>
                    <td>{c.employeur_code}</td>
                    <td>{c.fonction || "—"}</td>
                    <td>{c.statut}</td>
                    <td>
                      <button
                        type="button"
                        className="sa-btn sa-btn--ghost sa-btn--sm"
                        onClick={() => del(c)}
                        aria-label="Supprimer"
                      >
                        <Icon name="delete-02" className="i" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

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
            await load();
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
            await load();
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
  onClose,
  onDone,
  notify,
}: {
  employeurs: Employeur[];
  onClose: () => void;
  onDone: () => void;
  notify: (msg: string, type: "success" | "error") => void;
}) {
  const [matricule, setMatricule] = useState("");
  const [employeurCode, setEmployeurCode] = useState(employeurs[0]?.code ?? "");
  const [nom, setNom] = useState("");
  const [prenoms, setPrenoms] = useState("");
  const [email, setEmail] = useState("");
  const [telephone, setTelephone] = useState("");
  const [fonction, setFonction] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.createCollaborateur({
        matricule: matricule.trim().toUpperCase(),
        employeur_code: employeurCode,
        nom: nom.trim(),
        prenoms: prenoms.trim(),
        email: email.trim() || null,
        telephone: telephone.trim() || null,
        fonction: fonction.trim() || null,
        statut: "actif",
      });
      notify("Sociétaire ajouté.", "success");
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
          <h2 className="sa-card__title">Ajouter un sociétaire</h2>
        </div>
        <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label className="sa-form-label">Matricule</label>
              <input
                className="sa-input"
                required
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
              >
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
          <div>
            <label className="sa-form-label">Fonction (optionnel)</label>
            <input
              className="sa-input"
              value={fonction}
              onChange={(e) => setFonction(e.target.value)}
            />
          </div>
          <div
            style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}
          >
            <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" className="sa-btn sa-btn--primary" disabled={submitting}>
              {submitting ? "Enregistrement…" : "Ajouter"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ImportSocietairesModal({
  onClose,
  onDone,
  notify,
}: {
  onClose: () => void;
  onDone: () => void;
  notify: (msg: string, type: "success" | "error") => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState<{
    total_lines: number;
    accepted: number;
    rejected: number;
    errors: Array<{ line: number; error: string; data: any }>;
  } | null>(null);

  async function run() {
    if (!file) return;
    setUploading(true);
    setReport(null);
    try {
      const r = await api.uploadImport("collaborateurs", file);
      setReport(r);
      if (r.rejected > 0) {
        notify(`Import refusé : ${r.rejected} erreur(s) — aucune ligne insérée.`, "error");
      } else {
        notify(`${r.accepted} sociétaire(s) importé(s).`, "success");
      }
    } catch (e: any) {
      notify(e?.message ?? "Erreur.", "error");
    } finally {
      setUploading(false);
    }
  }

  const success = report && report.rejected === 0;

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
      <div
        className="sa-card"
        style={{ maxWidth: 720, width: "100%", margin: "32px auto" }}
      >
        <div className="sa-card__header">
          <h2 className="sa-card__title">Importer les sociétaires</h2>
          <p className="sa-card__desc">
            CSV (UTF-8) ou Excel (.xlsx) — max 10 Mo. Transaction atomique : aucune ligne
            n&apos;est insérée si une seule contient une erreur.
          </p>
        </div>
        {!report && (
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <a
                href={api.downloadImportTemplate("collaborateurs")}
                className="sa-btn sa-btn--ghost sa-btn--sm"
                download
              >
                <Icon name="download-02" className="i" />
                Télécharger le modèle CSV
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
                accept=".csv,.xlsx,.xls,text/csv"
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
                onClick={run}
                disabled={!file || uploading}
              >
                {uploading ? "Import en cours…" : "Lancer l'import"}
              </button>
            </div>
          </div>
        )}
        {report && (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", gap: 12 }}>
              <Metric label="Total" value={report.total_lines} />
              <Metric label="Acceptées" value={report.accepted} color="rgb(var(--color-brand-primary))" />
              <Metric
                label="Rejetées"
                value={report.rejected}
                color={
                  report.rejected > 0
                    ? "rgb(var(--color-feedback-error))"
                    : "rgb(var(--color-brand-primary))"
                }
              />
            </div>
            {report.errors.length > 0 ? (
              <div
                style={{
                  maxHeight: 240,
                  overflowY: "auto",
                  border: "1px solid rgb(var(--color-border-default, 230 230 230))",
                  borderRadius: 6,
                }}
              >
                <table className="sa-table">
                  <thead>
                    <tr>
                      <th style={{ width: 60 }}>Ligne</th>
                      <th>Erreur</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.errors.map((e, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: "monospace" }}>{e.line}</td>
                        <td>{e.error}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div
                className="sa-alert sa-alert--success"
                role="status"
                style={{ padding: 12 }}
              >
                <Icon name="checkmark-circle-02" className="i" />
                <span>{report.accepted} sociétaire(s) importé(s) avec succès.</span>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                type="button"
                className="sa-btn sa-btn--ghost"
                onClick={() => {
                  setReport(null);
                  setFile(null);
                }}
              >
                Nouvel import
              </button>
              <button
                type="button"
                className="sa-btn sa-btn--primary"
                onClick={() => (success ? onDone() : onClose())}
              >
                {success ? "Terminer" : "Fermer"}
              </button>
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
        padding: 12,
        background: "rgb(var(--color-bg-elevated, 245 245 245))",
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
