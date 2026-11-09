"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { useConfirm } from "@/components/ConfirmProvider";
import { StatusBadge } from "./_StatusBadge";
import type { Dossier } from "./_types";

type Props = {
  loading: boolean;
  items: Dossier[];
  search: string;
  hasFilter: boolean;
  onDeleted?: () => void;
  selected?: Set<string>;
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: (ids: string[]) => void;
};

/**
 * Tableau compact sans défilement horizontal : 5 colonnes, textes qui passent à la ligne,
 * badges nowrap, n° de dossier en mono, 1 action principale + menu « ⋯ ».
 */
export default function DossiersTable({
  loading, items, search, hasFilter, onDeleted,
  selected, onToggleSelect, onToggleSelectAll,
}: Props) {
  const allIds = items.map((d) => d.id);
  const allChecked = selected ? allIds.length > 0 && allIds.every((id) => selected.has(id)) : false;
  const someChecked = selected ? allIds.some((id) => selected.has(id)) : false;
  const canSelect = !!onToggleSelect && !!selected;

  return (
    <div className="sa-table-wrap" style={{ border: 0, borderTop: "1px solid rgb(var(--color-border-default))", borderRadius: 0, overflowX: "visible" }}>
      <table className="sa-table sa-table--cards" aria-busy={loading}>
        <caption className="sa-sr-only">Liste des dossiers d&apos;identification</caption>
        <thead>
          <tr>
            {canSelect && (
              <th scope="col" className="is-tight">
                <input
                  type="checkbox"
                  aria-label="Tout sélectionner"
                  checked={allChecked}
                  ref={(el) => {
                    if (el) el.indeterminate = !allChecked && someChecked;
                  }}
                  onChange={() => onToggleSelectAll?.(allIds)}
                />
              </th>
            )}
            <th scope="col">Dossier</th>
            <th scope="col">Sociétaire</th>
            <th scope="col">Statut</th>
            <th scope="col" className="hidden md:table-cell">Soumis le</th>
            <th scope="col" className="is-tight"><span className="sa-sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <SkeletonRows canSelect={canSelect} />
          ) : items.length === 0 ? (
            <tr><td colSpan={canSelect ? 6 : 5}><Empty query={search} hasFilter={hasFilter} /></td></tr>
          ) : (
            items.map((d) => (
              <DossierRow
                key={d.id}
                d={d}
                onDeleted={onDeleted}
                checked={selected?.has(d.id) || false}
                onToggleSelect={canSelect ? () => onToggleSelect?.(d.id) : undefined}
              />
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function SkeletonRows({ canSelect }: { canSelect?: boolean }) {
  return (
    <>
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i}>
          {canSelect && <td className="is-tight"><div className="sa-skeleton sa-skeleton--text" style={{ width: 16, height: 16 }} /></td>}
          <td><div className="sa-skeleton sa-skeleton--text" style={{ width: 120 }} /></td>
          <td><div className="sa-skeleton sa-skeleton--text" style={{ width: 160 }} /></td>
          <td><div className="sa-skeleton sa-skeleton--text" style={{ width: 90 }} /></td>
          <td className="hidden md:table-cell"><div className="sa-skeleton sa-skeleton--text" style={{ width: 90 }} /></td>
          <td><div className="sa-skeleton sa-skeleton--btn" style={{ width: 80 }} /></td>
        </tr>
      ))}
    </>
  );
}

function DossierRow({
  d, onDeleted, checked, onToggleSelect,
}: {
  d: Dossier;
  onDeleted?: () => void;
  checked?: boolean;
  onToggleSelect?: () => void;
}) {
  const href = `/dossiers/${d.id}`;
  const subParts = [d.matricule, d.employeur_code].filter(Boolean).join(" · ");
  return (
    <tr>
      {onToggleSelect && (
        <td className="is-tight" data-label="Sélection" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={!!checked}
            onChange={onToggleSelect}
            aria-label={`Sélectionner ${d.dossier_number}`}
          />
        </td>
      )}
      <td data-label="Dossier">
        <Link href={href} className="sa-row-link">{d.dossier_number}</Link>
        {d.numero_societaire && (
          <span className="sa-cell-sub sa-mono">{d.numero_societaire}</span>
        )}
        <DossierFlags d={d} />
      </td>
      <td data-label="Sociétaire">
        <span className="sa-cell-main">{d.end_user_name || "—"}</span>
        {(subParts || d.end_user_contact) && (
          <span className="sa-cell-sub">
            {subParts && <span className="sa-mono">{subParts}</span>}
            {subParts && d.end_user_contact ? " · " : ""}
            {d.end_user_contact}
          </span>
        )}
      </td>
      <td data-label="Statut"><StatusBadge status={d.status} /></td>
      <td className="hidden md:table-cell" data-label="Soumis le">
        <span className="sa-cell-sub" style={{ whiteSpace: "nowrap" }}>
          {d.submitted_at
            ? new Date(d.submitted_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
            : "—"}
        </span>
      </td>
      <td className="is-tight" data-label="Actions">
        <div className="sa-row" style={{ flexWrap: "nowrap", justifyContent: "flex-end", gap: 4 }}>
          <Link href={href} className="sa-btn sa-btn--outline sa-btn--sm" aria-label={`Ouvrir le dossier ${d.dossier_number}`}>
            <Icon name="view" className="i" />
            <span className="hidden lg:inline">Ouvrir</span>
          </Link>
          <a
            href={api.fichePdfUrl(d.id)}
            target="_blank"
            rel="noopener"
            className="sa-btn sa-btn--outline sa-btn--sm"
            aria-label={`Imprimer la fiche ${d.dossier_number}`}
          >
            <Icon name="printer" className="i" />
            <span className="hidden lg:inline">Imprimer</span>
          </a>
          <RowMenu d={d} href={href} onDeleted={onDeleted} />
        </div>
      </td>
    </tr>
  );
}

/** Menu « ⋯ » d'une ligne (accessible : bouton + menu, Échap / clic extérieur pour fermer). */
function RowMenu({ d, href, onDeleted }: { d: Dossier; href: string; onDeleted?: () => void }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [flipUp, setFlipUp] = useState(false);
  const confirm = useConfirm();
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    // Auto-flip : si la bulle n'a pas assez de place en dessous, on la remonte.
    const btn = triggerRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const needed = 180; // hauteur approximative du menu (3 items)
    setFlipUp(spaceBelow < needed && rect.top > needed);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function remove() {
    setOpen(false);
    const ok = await confirm({
      title: `Supprimer définitivement ${d.dossier_number} ?`,
      message:
        "Cette action est IRRÉVERSIBLE : le dossier, ses pièces, consentements et données professionnelles sont purgés de la base. Le journal d'audit conserve une trace. À réserver au nettoyage de tests ou à une demande RGPD d'effacement complet.",
      confirmText: "Supprimer définitivement",
      cancelText: "Annuler",
      variant: "danger",
      icon: "warn",
    });
    if (!ok) return;
    setDeleting(true);
    try {
      await api.deleteDossier(d.id);
      onDeleted?.();
    } catch (e: any) {
      alert("Suppression impossible : " + (e?.message || "erreur serveur"));
    } finally {
      setDeleting(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(d.dossier_number);
      setCopied(true);
      setTimeout(() => { setCopied(false); setOpen(false); }, 1200);
    } catch {
      setOpen(false);
    }
  }

  return (
    <div className="sa-popover-anchor" ref={ref}>
      <button
        ref={triggerRef}
        type="button"
        className="sa-icon-btn"
        style={{ width: 36, height: 36 }}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Autres actions pour ${d.dossier_number}`}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="more-horizontal" className="i" />
      </button>
      {open && (
        <div
          className="sa-menu"
          role="menu"
          style={{
            width: 220,
            ...(flipUp
              ? { top: "auto", bottom: "calc(100% + 8px)" }
              : {}),
          }}
        >
          <Link href={href} role="menuitem" className="sa-menu__item" onClick={() => setOpen(false)}>
            <Icon name="view" className="i" /> Ouvrir le dossier
          </Link>
          <button type="button" role="menuitem" className="sa-menu__item" onClick={copy}>
            <Icon name={copied ? "tick-02" : "copy-01"} className="i" />
            {copied ? "Numéro copié" : "Copier le n° de dossier"}
          </button>
          <button
            type="button"
            role="menuitem"
            className="sa-menu__item"
            onClick={remove}
            disabled={deleting}
            style={{ color: "rgb(var(--color-danger, 220 38 38))" }}
          >
            <Icon name="delete-02" className="i" />
            {deleting ? "Suppression…" : "Supprimer définitivement"}
          </button>
        </div>
      )}
    </div>
  );
}

/** Indicateurs : priorité / retard / verrouillage — icône + texte, jamais coupés. */
function DossierFlags({ d }: { d: Dossier }) {
  if (!d.priority_review && !d.is_overdue && !d.locked) return null;
  return (
    <div className="sa-row" style={{ gap: 4, marginTop: 4 }}>
      {d.priority_review && (
        <span className="sa-badge sa-badge--warn" title={d.priority_reason ?? "À revoir en priorité"}>
          <Icon name="flag-01" className="i" /> Priorité
        </span>
      )}
      {d.is_overdue && (
        <span
          className="sa-badge sa-badge--error"
          title={`En attente depuis ${d.age_hours ? Math.round(d.age_hours) : "?"} heures`}
        >
          <Icon name="alarm-clock" className="i" /> {d.age_hours ? Math.round(d.age_hours) : "?"} h
        </span>
      )}
      {d.locked && (
        <span className="sa-badge sa-badge--info" title="Un autre agent traite ce dossier">
          <Icon name="lock-key" className="i" /> En traitement
        </span>
      )}
    </div>
  );
}

function Empty({ query, hasFilter }: { query: string; hasFilter: boolean }) {
  return (
    <div className="sa-empty">
      <Icon name="folder-01" className="i" />
      <div className="sa-empty__title">
        {query ? "Aucun résultat" : hasFilter ? "Aucun dossier dans ce statut" : "Aucun dossier pour le moment"}
      </div>
      <p className="sa-empty__text">
        {query
          ? `Aucun dossier ne correspond à « ${query} ».`
          : "Démarrez une conversation avec l'assistant via le chat web ou WhatsApp pour générer le premier dossier."}
      </p>
    </div>
  );
}
