"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Landing "/" — redirige vers /dossiers ; l'AuthGuard s'occupe de renvoyer
 * vers /login si aucune session valide n'est trouvée.
 */
export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dossiers");
  }, [router]);
  return (
    <div className="ma2e-public" style={{ alignItems: "center", justifyContent: "center" }} role="status" aria-label="Redirection en cours">
      <span className="sa-spinner" />
    </div>
  );
}
