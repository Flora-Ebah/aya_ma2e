"use client";
import { useState } from "react";
import { Icon } from "@/components/Icon";
import { Modal } from "@/components/ui";
import { ACTION_LABELS, MODULE_LABELS, type BusinessRole, type User } from "./_types";

type Props = {
  user: User;
  allRoles: BusinessRole[];
  currentRoles: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSubmit: (selectedIds: string[]) => void;
};

/**
 * Attribution des rôles métier : liste de cases à cocher (cartes de choix) à
 * gauche, aperçu compact des permissions du rôle survolé / focalisé à droite.
 * Pas de défilement : l'aperçu est un récapitulatif texte (module : actions).
 */
export default function EditRolesModal({ user, allRoles, currentRoles, onClose, onSubmit }: Props) {
  const [selectedIds, setSelectedIds] = useState<string[]>(currentRoles.map((r) => r.id));
  const [focusedRoleId, setFocusedRoleId] = useState<string | null>(
    currentRoles[0]?.id ?? allRoles[0]?.id ?? null,
  );

  const toggle = (id: string) =>
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const focusedRole = allRoles.find((r) => r.id === focusedRoleId) || null;

  return (
    <Modal
      open
      onClose={onClose}
      title="Gérer les rôles métier"
      subtitle={`${user.name} · ${user.email}`}
      size="xl"
      footer={<>
        <span className="sa-dialog__footer-start sa-micro" style={{ marginRight: "auto" }}>
          {selectedIds.length} rôle(s) sélectionné(s)
        </span>
        <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
        <button type="button" className="sa-btn sa-btn--primary" onClick={() => onSubmit(selectedIds)}>
          Enregistrer
        </button>
      </>}
    >
      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-4 items-start">
        <fieldset className="sa-fieldset" style={{ padding: 0, border: 0 }}>
          <legend className="sa-label" style={{ marginBottom: 8 }}>Rôles disponibles</legend>
          {allRoles.length === 0 ? (
            <p className="sa-help">
              Aucun rôle disponible. Créez-en depuis « Administration → Rôles &amp; permissions ».
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {allRoles.map((r) => (
                <label
                  key={r.id}
                  className="sa-choice"
                  onMouseEnter={() => setFocusedRoleId(r.id)}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(r.id)}
                    onChange={() => toggle(r.id)}
                    onFocus={() => setFocusedRoleId(r.id)}
                  />
                  <span className="sa-choice__body">
                    <span className="sa-choice__title">{r.name}</span>
                    {r.description && <span className="sa-choice__desc">{r.description}</span>}
                  </span>
                </label>
              ))}
            </div>
          )}
        </fieldset>
        <PermissionsSummary role={focusedRole} />
      </div>
    </Modal>
  );
}

function PermissionsSummary({ role }: { role: BusinessRole | null }) {
  return (
    <div className="sa-card" aria-live="polite" style={{ background: "rgb(var(--color-bg-surface-subtle))" }}>
      <div className="sa-label">{role ? `Permissions de « ${role.name} »` : "Permissions"}</div>
      {!role ? (
        <p className="sa-help">Survolez ou sélectionnez un rôle pour voir ses permissions.</p>
      ) : (
        <dl className="sa-kv" style={{ gridTemplateColumns: "minmax(110px, max-content) minmax(0, 1fr)" }}>
          {Object.keys(MODULE_LABELS).map((m) => {
            const allowed = Object.keys(ACTION_LABELS).filter((a) => role.permissions?.[m]?.[a]);
            return (
              <div key={m} style={{ display: "contents" }}>
                <dt>{MODULE_LABELS[m]}</dt>
                <dd style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {allowed.length === 0 ? (
                    <span className="sa-badge sa-badge--neutral">
                      <Icon name="minus-sign" className="i" />
                      Aucune
                    </span>
                  ) : allowed.map((a) => (
                    <span key={a} className="sa-badge sa-badge--ok">
                      <Icon name="tick-02" className="i" />
                      {ACTION_LABELS[a]}
                    </span>
                  ))}
                </dd>
              </div>
            );
          })}
        </dl>
      )}
    </div>
  );
}
