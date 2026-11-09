"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Profil utilisateur MA2E (issu de /api/me).
 * Aucune info sensible : nom, email, rôle, tenant. Le token JWT reste dans
 * un cookie httpOnly côté serveur (jamais exposé ici).
 */
export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: "super_admin" | "tenant_admin" | "agent" | "viewer";
  tenant_id: string | null;
  auth_method?: "password" | "ad";
};

type Ctx = {
  user: CurrentUser | null;
  loading: boolean;
  /** Force un re-fetch depuis /api/me. Appelé après login/logout. */
  refresh: () => Promise<void>;
  clear: () => void;
};

const CurrentUserContext = createContext<Ctx | undefined>(undefined);

/**
 * Provider qui fetch /api/me au montage et conserve le profil en state React
 * (jamais en localStorage). Le fetch réutilise le cookie de session httpOnly
 * envoyé automatiquement par le navigateur.
 */
export function CurrentUserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api.me();
      // /api/me ne renvoie que l'identifiant, le rôle et les permissions : on
      // complète nom / e-mail via /api/users/{id} (réservé aux administrateurs).
      const uid = me?.user_id ?? me?.id;
      if (me && uid && !me.name) {
        try {
          const detail = await api.getUser(uid);
          setUser({ ...me, id: uid, name: detail?.name ?? "", email: detail?.email ?? me.email });
          return;
        } catch {
          /* profil détaillé indisponible (rôle non administrateur) */
        }
      }
      setUser(me ? { ...me, id: uid ?? me.id } : me);
    } catch {
      // Pas de session → user reste null. Les guards redirigent vers /login.
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setUser(null);
  }, []);

  useEffect(() => {
    // Purge le cache localStorage hérité de la version précédente.
    try {
      localStorage.removeItem("ma2e_user");
    } catch { /* mode privé strict */ }
    void refresh();
  }, [refresh]);

  return (
    <CurrentUserContext.Provider value={{ user, loading, refresh, clear }}>
      {children}
    </CurrentUserContext.Provider>
  );
}

/** Hook d'accès au profil utilisateur courant. */
export function useCurrentUser(): Ctx {
  const ctx = useContext(CurrentUserContext);
  if (!ctx) {
    throw new Error("useCurrentUser must be used inside <CurrentUserProvider>");
  }
  return ctx;
}
