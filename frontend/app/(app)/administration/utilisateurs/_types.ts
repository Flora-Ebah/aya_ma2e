export type User = {
  id: string;
  tenant_id: string | null;
  email: string;
  name: string;
  role: "super_admin" | "tenant_admin" | "agent";
  auth_method: "password" | "ad";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type BusinessRole = {
  id: string;
  name: string;
  description: string | null;
  permissions: Record<string, Record<string, boolean>>;
};

export const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super-admin",
  tenant_admin: "Administrateur",
  agent: "Gestionnaire",
};

export const MODULE_LABELS: Record<string, string> = {
  validation: "Validation",
  reporting: "Reporting",
  administration: "Administration",
  audit: "Audit",
  conformite: "Conformité",
};

export const ACTION_LABELS: Record<string, string> = {
  read: "Lire",
  write: "Modifier",
  delete: "Supprimer",
  export: "Exporter",
};
