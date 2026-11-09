"use client";
import { useId, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useConfirm, useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";
import { Card, DropdownMenu, EmptyState, Modal, PageHeader, Spinner } from "@/components/ui";
import PermissionsMatrix from "./_PermissionsMatrix";

type Role = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  permissions: Record<string, Record<string, boolean>>;
  is_active: boolean;
};

type Schema = { modules: string[]; actions: string[] };
type RolePayload = { name: string; description: string; permissions: any };

export default function RolesPage() {
  const confirm = useConfirm();
  const toast = useToast();
  const { data: schema } = useApi<Schema>(() => api.rolesPermissionsSchema());
  const { data: roles = [], loading, refetch } = useApi<Role[]>(() => api.listRoles());
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  async function seedDefaults() {
    try {
      const r = await api.seedDefaultRoles();
      toast({
        tone: "success",
        title: r.created > 0 ? `${r.created} rôle(s) installé(s)` : "Déjà installés",
        message: "Agent Validateur · Superviseur · Lecteur · IT",
      });
      await refetch();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function deleteRole(role: Role) {
    const ok = await confirm({
      title: "Supprimer ce rôle ?",
      message: (
        <>Le rôle <strong>{role.name}</strong> sera supprimé. Si des utilisateurs le portent
        encore, l&apos;opération sera refusée et il faudra les désaffecter d&apos;abord.</>
      ),
      confirmText: "Supprimer",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await api.deleteRole(role.id);
      toast({ tone: "info", title: "Rôle supprimé", message: role.name });
      await refetch();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function saveRole(payload: RolePayload, id?: string) {
    try {
      if (id) {
        await api.updateRole(id, payload);
        toast({ tone: "success", title: "Rôle mis à jour", message: payload.name });
      } else {
        await api.createRole(payload);
        toast({ tone: "success", title: "Rôle créé", message: payload.name });
      }
      setCreateOpen(false);
      setEditingRole(null);
      await refetch();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  const showEditor = createOpen || editingRole !== null;
  const list = roles ?? [];

  return (
    <>
      <div>
        <PageHeader
          eyebrow="Administration"
          title="Rôles & permissions"
          subtitle={
            "Rôles métier nommés (Agent Validateur, Superviseur, Lecteur, IT…) avec "
            + "permissions fines par module. Un utilisateur peut porter plusieurs rôles (US-04)."
          }
          actions={<>
            {list.length === 0 && (
              <button type="button" className="sa-btn sa-btn--outline" onClick={seedDefaults}>
                Installer les 4 rôles MA2E
              </button>
            )}
            <button type="button" className="sa-btn sa-btn--primary" onClick={() => setCreateOpen(true)}>
              <Icon name="plus-sign" className="i" />
              Nouveau rôle
            </button>
          </>}
        />

        {loading && <Card><div className="py-8 flex justify-center"><Spinner /></div></Card>}
        {!loading && list.length === 0 && (
          <Card>
            <EmptyState
              title="Aucun rôle métier défini"
              description="Cliquez sur « Installer les 4 rôles MA2E » pour démarrer rapidement."
            />
          </Card>
        )}
        {!loading && list.length > 0 && schema && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-stretch xl:[&>:last-child:nth-child(odd)]:col-span-2">
            {list.map((r) => (
              <RoleCard
                key={r.id}
                role={r}
                schema={schema}
                onEdit={() => setEditingRole(r)}
                onDelete={() => deleteRole(r)}
              />
            ))}
          </div>
        )}
      </div>

      {showEditor && schema && (
        <RoleEditorModal
          open={showEditor}
          schema={schema}
          initial={editingRole}
          onClose={() => { setCreateOpen(false); setEditingRole(null); }}
          onSubmit={(payload) => saveRole(payload, editingRole?.id)}
        />
      )}
    </>
  );
}

function RoleCard({ role, schema, onEdit, onDelete }: {
  role: Role; schema: Schema; onEdit: () => void; onDelete: () => void;
}) {
  return (
    <section className="sa-card" style={{ height: "100%" }} aria-label={`Rôle ${role.name}`}>
      <div className="sa-card__header">
        <div>
          <h2 className="sa-card__title" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {role.name}
            {!role.is_active && <span className="sa-badge sa-badge--neutral">Inactif</span>}
          </h2>
          {role.description && <p className="sa-card__subtitle">{role.description}</p>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <button type="button" className="sa-btn sa-btn--outline sa-btn--sm" onClick={onEdit}>
            <Icon name="edit-02" className="i" />
            Modifier
          </button>
          <DropdownMenu
            label={`Autres actions pour le rôle ${role.name}`}
            items={[{ label: "Supprimer le rôle", icon: "delete-02", danger: true, onClick: onDelete }]}
          />
        </div>
      </div>
      <div style={{ marginTop: "auto" }}>
        <PermissionsMatrix schema={schema} permissions={role.permissions} readOnly />
      </div>
    </section>
  );
}

function RoleEditorModal({ open, schema, initial, onClose, onSubmit }: {
  open: boolean;
  schema: Schema;
  initial: Role | null;
  onClose: () => void;
  onSubmit: (payload: RolePayload) => void;
}) {
  const uid = useId();
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [perms, setPerms] = useState<Record<string, Record<string, boolean>>>(() => {
    if (initial?.permissions) return JSON.parse(JSON.stringify(initial.permissions));
    const out: any = {};
    schema.modules.forEach((m) => {
      out[m] = {};
      schema.actions.forEach((a) => (out[m][a] = false));
    });
    return out;
  });

  const toggle = (m: string, a: string) =>
    setPerms((prev) => ({ ...prev, [m]: { ...prev[m], [a]: !prev[m]?.[a] } }));

  const toggleRow = (m: string) => {
    const allOn = schema.actions.every((a) => perms[m]?.[a]);
    setPerms((prev) => ({
      ...prev,
      [m]: Object.fromEntries(schema.actions.map((a) => [a, !allOn])),
    }));
  };

  const valid = name.trim().length > 0;
  const submit = () => onSubmit({ name: name.trim(), description: description.trim(), permissions: perms });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={initial ? `Modifier « ${initial.name} »` : "Nouveau rôle métier"}
      size="lg"
      footer={<>
        <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
        <button type="button" className="sa-btn sa-btn--primary" onClick={submit} disabled={!valid}>
          {initial ? "Enregistrer" : "Créer"}
        </button>
      </>}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="sa-form-grid">
          <div className="sa-field">
            <label className="sa-label" htmlFor={`${uid}-n`}>Nom du rôle <span className="sa-req" aria-hidden="true">*</span></label>
            <input
              id={`${uid}-n`} className="sa-input" value={name} required
              onChange={(e) => setName(e.target.value)} placeholder="ex. Agent Validateur Senior"
            />
          </div>
          <div className="sa-field">
            <div className="sa-label-row">
              <label className="sa-label" htmlFor={`${uid}-d`}>Description</label>
              <span className="sa-label__opt">facultatif</span>
            </div>
            <input
              id={`${uid}-d`} className="sa-input" value={description}
              onChange={(e) => setDescription(e.target.value)} placeholder="À quoi sert ce rôle ?"
            />
          </div>
        </div>
        <fieldset className="sa-fieldset">
          <legend className="sa-label" style={{ marginBottom: 8 }}>Permissions</legend>
          <PermissionsMatrix schema={schema} permissions={perms} onToggle={toggle} onToggleRow={toggleRow} />
        </fieldset>
      </div>
    </Modal>
  );
}
