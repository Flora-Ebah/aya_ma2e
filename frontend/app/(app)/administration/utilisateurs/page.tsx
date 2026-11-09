"use client";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useConfirm, useToast } from "@/components/ConfirmProvider";
import { useCurrentUser } from "@/components/CurrentUserProvider";
import { Icon } from "@/components/Icon";
import { PageHeader } from "@/components/ui";
import CreateUserModal from "./_CreateUserModal";
import EditRolesModal from "./_EditRolesModal";
import ResetPasswordModal from "./_ResetPasswordModal";
import UsersTable from "./_UsersTable";
import { useUsersList } from "./_useUsersList";
import { ROLE_LABELS, type User } from "./_types";

const PAGE_SIZE = 10;

export default function UtilisateursPage() {
  const confirm = useConfirm();
  const toast = useToast();
  const { user: me } = useCurrentUser();

  const { users, availableRoles, userRolesMap, loading, reload } = useUsersList();

  const [createOpen, setCreateOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [editRolesTarget, setEditRolesTarget] = useState<User | null>(null);

  // Filtres (côté client) : recherche, rôle système, statut.
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const meId = me?.id;
  const canAdminister = me?.role === "super_admin" || me?.role === "tenant_admin";

  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      if (roleFilter && u.role !== roleFilter) return false;
      if (statusFilter === "actif" && !u.is_active) return false;
      if (statusFilter === "inactif" && u.is_active) return false;
      if (!q) return true;
      return u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
    });
  }, [users, search, roleFilter, statusFilter]);

  const pageCount = Math.max(1, Math.ceil(filteredUsers.length / PAGE_SIZE));
  useEffect(() => { setPage(1); }, [search, roleFilter, statusFilter]);
  useEffect(() => { if (page > pageCount) setPage(pageCount); }, [page, pageCount]);
  const pagedUsers = filteredUsers.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const hasFilter = Boolean(search.trim() || roleFilter || statusFilter);

  function guardSelf(u: User, action: string): boolean {
    if (u.id === meId) {
      toast({ tone: "error", title: "Action interdite", message: action });
      return false;
    }
    return true;
  }

  async function onSaveUserRoles(u: User, selectedRoleIds: string[]) {
    const currentIds = (userRolesMap[u.id] || []).map((r) => r.id);
    const toAdd = selectedRoleIds.filter((id) => !currentIds.includes(id));
    const toRemove = currentIds.filter((id) => !selectedRoleIds.includes(id));
    try {
      await Promise.all([
        ...toAdd.map((rid) => api.assignRoleToUser(u.id, rid)),
        ...toRemove.map((rid) => api.revokeRoleFromUser(u.id, rid)),
      ]);
      toast({ tone: "success", title: "Rôles mis à jour", message: `${u.name} : +${toAdd.length} / -${toRemove.length}` });
      setEditRolesTarget(null);
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function onCreate(payload: any) {
    try {
      const body: any = {
        email: payload.email,
        name: payload.name,
        role: payload.role,
        auth_method: payload.auth_method,
      };
      if (payload.auth_method === "password") body.password = payload.password;
      await api.createUser(body);
      toast({ tone: "success", title: "Utilisateur créé", message: payload.email });
      setCreateOpen(false);
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function onToggleActive(u: User) {
    if (!guardSelf(u, "Vous ne pouvez pas vous désactiver vous-même.")) return;
    const action = u.is_active ? "désactiver" : "réactiver";
    const ok = await confirm({
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} cet utilisateur ?`,
      message: <>L&apos;utilisateur <strong>{u.name}</strong> ({u.email}) va être {action}.</>,
      confirmText: action.charAt(0).toUpperCase() + action.slice(1),
      variant: u.is_active ? "danger" : "default",
    });
    if (!ok) return;
    try {
      await api.updateUser(u.id, { is_active: !u.is_active });
      toast({ tone: "success", title: `Utilisateur ${action === "désactiver" ? "désactivé" : "réactivé"}`, message: u.email });
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function onChangeRole(u: User, newRole: User["role"]) {
    if (!guardSelf(u, "Vous ne pouvez pas modifier votre propre rôle.")) return;
    try {
      await api.updateUser(u.id, { role: newRole });
      toast({ tone: "success", title: "Rôle mis à jour", message: u.email });
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function onResetPassword(newPassword: string) {
    if (!resetTarget) return;
    try {
      await api.resetUserPassword(resetTarget.id, newPassword);
      toast({ tone: "success", title: "Mot de passe réinitialisé", message: resetTarget.email });
      setResetTarget(null);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  return (
    <>
      <div>
        <PageHeader
          eyebrow="Administration"
          title="Utilisateurs back-office"
          subtitle="Gestion des comptes administrateurs et gestionnaires. Modifications versionnées et auditées."
          actions={canAdminister && (
            <button type="button" className="sa-btn sa-btn--primary" onClick={() => setCreateOpen(true)}>
              <Icon name="user-add-01" className="i" />
              Nouvel utilisateur
            </button>
          )}
        />

        <section className="sa-card sa-card--flush" aria-label="Liste des comptes">
          <div className="sa-toolbar" style={{ flexWrap: "nowrap", alignItems: "center" }} role="search">
            <div className="sa-input-group" style={{ flex: "1 1 220px", minWidth: 0 }}>
              <Icon name="search-01" className="i" />
              <input
                type="search" className="sa-input" value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher un nom ou un e-mail…"
                aria-label="Rechercher un utilisateur"
              />
            </div>
            <select
              className="sa-select" style={{ flex: "0 1 200px", minWidth: 0 }}
              value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}
              aria-label="Filtrer par rôle système"
            >
              <option value="">Tous les rôles</option>
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select
              className="sa-select" style={{ flex: "0 1 160px", minWidth: 0 }}
              value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filtrer par statut"
            >
              <option value="">Tous statuts</option>
              <option value="actif">Actifs</option>
              <option value="inactif">Inactifs</option>
            </select>
          </div>

          <UsersTable
            loading={loading}
            users={pagedUsers}
            filtered={hasFilter}
            meRole={me?.role}
            meId={meId}
            userRolesMap={userRolesMap}
            canAdminister={canAdminister}
            hasAvailableRoles={availableRoles.length > 0}
            onEditRoles={setEditRolesTarget}
            onChangeRole={onChangeRole}
            onResetPassword={setResetTarget}
            onToggleActive={onToggleActive}
          />

          {!loading && filteredUsers.length > 0 && (
            <div className="sa-pagination-bar">
              <span className="sa-pagination__info" aria-live="polite">
                {filteredUsers.length} compte(s) · page {page} / {pageCount}
              </span>
              <nav className="sa-pagination" aria-label="Pagination des comptes">
                <button
                  type="button" className="sa-btn sa-btn--outline sa-btn--sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
                >
                  <Icon name="arrow-left-01" className="i" />
                  Précédent
                </button>
                <button
                  type="button" className="sa-btn sa-btn--outline sa-btn--sm"
                  onClick={() => setPage((p) => Math.min(pageCount, p + 1))} disabled={page >= pageCount}
                >
                  Suivant
                  <Icon name="arrow-right-01" className="i" />
                </button>
              </nav>
            </div>
          )}
        </section>
      </div>

      <CreateUserModal
        open={createOpen}
        isSuperAdmin={me?.role === "super_admin"}
        onClose={() => setCreateOpen(false)}
        onSubmit={onCreate}
      />

      <ResetPasswordModal
        open={!!resetTarget}
        user={resetTarget}
        onClose={() => setResetTarget(null)}
        onSubmit={onResetPassword}
      />

      {editRolesTarget && (
        <EditRolesModal
          user={editRolesTarget}
          allRoles={availableRoles}
          currentRoles={userRolesMap[editRolesTarget.id] || []}
          onClose={() => setEditRolesTarget(null)}
          onSubmit={(ids) => onSaveUserRoles(editRolesTarget, ids)}
        />
      )}
    </>
  );
}
