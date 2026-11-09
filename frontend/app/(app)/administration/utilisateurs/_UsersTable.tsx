"use client";
import { Icon } from "@/components/Icon";
import { DropdownMenu, EmptyState, Spinner, type MenuItem } from "@/components/ui";
import { ROLE_LABELS, type User } from "./_types";

type Props = {
  loading: boolean;
  users: User[];
  /** Vrai si la liste est vide à cause des filtres (et non faute de comptes). */
  filtered?: boolean;
  meRole?: string;
  meId?: string;
  userRolesMap: Record<string, Array<{ id: string; name: string }>>;
  canAdminister: boolean;
  hasAvailableRoles: boolean;
  onEditRoles: (u: User) => void;
  onChangeRole: (u: User, newRole: User["role"]) => void;
  onResetPassword: (u: User) => void;
  onToggleActive: (u: User) => void;
};

/**
 * Tableau des comptes : 5 colonnes compactes, sans défilement horizontal
 * (passage en cartes sous 768 px). Par ligne : 1 action principale visible
 * (« Rôles ») + menu « ⋯ ».
 */
export default function UsersTable(props: Props) {
  const { loading, users, filtered } = props;
  if (loading) return <div className="p-12 flex justify-center"><Spinner /></div>;
  if (users.length === 0) {
    return (
      <EmptyState
        title={filtered ? "Aucun résultat" : "Aucun utilisateur"}
        description={filtered
          ? "Aucun compte ne correspond à ces filtres."
          : "Créez le premier compte avec le bouton « Nouvel utilisateur »."}
      />
    );
  }
  return (
    <div className="sa-table-wrap">
      <table className="sa-table sa-table--compact sa-table--cards">
        <thead>
          <tr>
            <th scope="col">Utilisateur</th>
            <th scope="col">Rôles</th>
            <th scope="col">Dernière connexion</th>
            <th scope="col">Statut</th>
            <th scope="col" className="is-tight"><span className="sa-sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => <UserRow key={u.id} u={u} {...props} />)}
        </tbody>
      </table>
    </div>
  );
}

function UserRow({
  u, meRole, meId, userRolesMap, canAdminister, hasAvailableRoles,
  onEditRoles, onChangeRole, onResetPassword, onToggleActive,
}: Props & { u: User }) {
  const isSelf = u.id === meId;
  const roles = userRolesMap[u.id] || [];

  const items: MenuItem[] = [];
  if (canAdminister) {
    if (u.auth_method === "password") {
      items.push({ label: "Réinitialiser le mot de passe", icon: "lock-password", onClick: () => onResetPassword(u) });
    }
    if (!isSelf) {
      if (items.length > 0) items.push({ separator: true, key: "sep-roles" });
      (["agent", "tenant_admin", ...(meRole === "super_admin" ? ["super_admin"] : [])] as User["role"][])
        .filter((r) => r !== u.role)
        .forEach((r) => items.push({
          label: `Passer en ${ROLE_LABELS[r].toLowerCase()}`,
          icon: "user-check-01",
          onClick: () => onChangeRole(u, r),
        }));
      items.push({ separator: true, key: "sep-active" });
      items.push({
        label: u.is_active ? "Désactiver le compte" : "Réactiver le compte",
        icon: u.is_active ? "cancel-circle" : "checkmark-circle-02",
        danger: u.is_active,
        onClick: () => onToggleActive(u),
      });
    }
  }

  return (
    <tr style={!u.is_active ? { opacity: 0.75 } : undefined}>
      <td data-label="Utilisateur">
        <div className="sa-cell-main" style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          {u.name}
          {isSelf && <span className="sa-badge sa-badge--brand">Vous</span>}
          {u.auth_method === "ad" && (
            <span className="sa-badge sa-badge--accent" title="Authentification Active Directory ERANOVE">AD</span>
          )}
        </div>
        <span className="sa-cell-sub sa-mono">{u.email}</span>
      </td>

      <td data-label="Rôles">
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 4 }}>
          <span className="sa-badge sa-badge--outline sa-badge--neutral" title="Rôle système (technique)">
            <Icon name="shield-user" className="i" />
            {ROLE_LABELS[u.role]}
          </span>
          {roles.map((r) => <span key={r.id} className="sa-badge sa-badge--brand">{r.name}</span>)}
          {roles.length === 0 && <span className="sa-cell-sub">Aucun rôle métier</span>}
        </div>
      </td>

      <td data-label="Dernière connexion" className="sa-text-soft">
        {u.last_login_at
          ? new Date(u.last_login_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
          : "—"}
      </td>

      <td data-label="Statut">
        <span className={`sa-badge ${u.is_active ? "sa-badge--ok" : "sa-badge--neutral"}`}>
          <Icon name={u.is_active ? "checkmark-circle-02" : "pause-circle"} className="i" />
          {u.is_active ? "Actif" : "Inactif"}
        </span>
      </td>

      <td className="is-tight">
        {canAdminister && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>
            {!isSelf && hasAvailableRoles && (
              <button
                type="button"
                className="sa-btn sa-btn--outline sa-btn--sm"
                onClick={() => onEditRoles(u)}
                aria-label={`Gérer les rôles de ${u.name}`}
              >
                <Icon name="user-group" className="i" />
                Rôles
              </button>
            )}
            {items.length > 0 && <DropdownMenu label={`Autres actions pour ${u.name}`} items={items} />}
          </div>
        )}
      </td>
    </tr>
  );
}
