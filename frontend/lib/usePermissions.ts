"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export type PermissionMatrix = Record<string, Record<string, boolean>>;

export type MePermissions = {
  role_system: "super_admin" | "tenant_admin" | "agent";
  is_super_admin: boolean;
  permissions: PermissionMatrix;
  modules: string[];
  actions: string[];
};

/**
 * Hook React qui charge les permissions effectives de l'utilisateur connecté
 * depuis `/api/me/permissions`. Cache en mémoire (rechargé à chaque mount).
 *
 * Usage :
 *   const { can, loading, perms } = usePermissions();
 *   if (can("validation", "write")) { ... }
 */
export function usePermissions() {
  const [perms, setPerms] = useState<MePermissions | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Le cookie httpOnly est envoyé automatiquement — pas besoin de vérifier
    // un token localement. Si la session est absente, l'API retourne 401 et
    // on aboutit dans le .catch avec perms=null.
    api
      .myPermissions()
      .then((p: MePermissions) => setPerms(p))
      .catch(() => setPerms(null))
      .finally(() => setLoading(false));
  }, []);

  function can(module: string, action: string): boolean {
    if (!perms) return false;
    if (perms.is_super_admin) return true;
    if (perms.role_system === "tenant_admin") return true;
    return Boolean(perms.permissions?.[module]?.[action]);
  }

  return { perms, loading, can };
}
