"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import type { BusinessRole, User } from "./_types";

/**
 * Charge la liste des utilisateurs, les rôles métier disponibles,
 * et la map user_id → rôles métier assignés.
 */
export function useUsersList() {
  const toast = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [availableRoles, setAvailableRoles] = useState<BusinessRole[]>([]);
  const [userRolesMap, setUserRolesMap] = useState<Record<string, Array<{ id: string; name: string }>>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => { void load().finally(() => setLoading(false)); }, []);

  async function load() {
    try {
      const [data, roles] = await Promise.all([
        api.listUsers(true),
        api.listRoles().catch(() => []),
      ]);
      setUsers(data);
      setAvailableRoles(roles);
      const map: Record<string, Array<{ id: string; name: string }>> = {};
      await Promise.all(
        data.map(async (u: any) => {
          try {
            const rs = await api.listUserRoles(u.id);
            map[u.id] = rs.map((r: any) => ({ id: r.id, name: r.name }));
          } catch {
            map[u.id] = [];
          }
        })
      );
      setUserRolesMap(map);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  return { users, availableRoles, userRolesMap, loading, reload: load };
}
