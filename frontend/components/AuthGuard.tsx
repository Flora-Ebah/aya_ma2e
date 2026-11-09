"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, logout } from "@/lib/api";

/**
 * Vérifie côté serveur (via `/api/me`) que la session cookie httpOnly est
 * encore valide, AVANT d'afficher toute page protégée. Sans ce garde, un
 * utilisateur sans cookie verrait pendant ~1s l'UI apparaître avant que le
 * premier appel API renvoie 401 — mauvaise UX et fuite d'information
 * (structure de la sidebar, libellés des pages, etc.).
 *
 * Le contrat avec le backend :
 *  - `/api/me` avec cookie valide → 200 + profil utilisateur
 *  - sinon → 401 (intercepté dans `api.ts` qui redirige déjà vers /login)
 *
 * Wrap ce composant dans le layout des routes protégées.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await api.me();
        if (!cancelled) setChecked(true);
      } catch {
        // Le 401 déclenche déjà logout()+redirect dans `api.ts`. Ce catch
        // filet évite le crash React si la promesse rejette pour toute
        // autre raison (réseau KO, CORS, etc.).
        if (!cancelled) {
          await logout();
          const next = encodeURIComponent(pathname || "/dossiers");
          router.replace(`/login?next=${next}`);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (!checked) {
    // Écran neutre pendant la vérification. Aucune info métier visible.
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas" role="status" aria-label="Vérification de la session">
        <span className="sa-spinner" />
      </div>
    );
  }

  return <>{children}</>;
}
