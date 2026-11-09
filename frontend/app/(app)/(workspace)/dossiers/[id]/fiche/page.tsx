"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import FicheInscription from "./_FicheInscription";
import "./fiche.css";

/**
 * Page impression de la fiche sociétaire.
 *   - GET /dossiers/<id>/fiche          → fiche unique
 *   - GET /dossiers/fiches?ids=a,b,c    → N fiches à la suite (une par page A4)
 *     (gérée par l'autre route /dossiers/fiches)
 *
 * Auto-print sur `?print=1` ou après chargement complet.
 */
export default function FichePage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const [dossier, setDossier] = useState<any>(null);
  const [me, setMe] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const printedRef = useRef(false);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [d, user] = await Promise.all([
          api.getDossier(params.id),
          api.me().catch(() => null),
        ]);
        if (cancel) return;
        setDossier(d);
        setMe(user);
      } catch (e: any) {
        setError(e?.message || "Erreur de chargement.");
      }
    })();
    return () => { cancel = true; };
  }, [params.id]);

  useEffect(() => {
    if (!dossier || printedRef.current) return;
    if (search.get("print") !== "1") return;
    printedRef.current = true;
    // Laisse le temps aux images (MinIO) de charger.
    const t = setTimeout(() => window.print(), 600);
    return () => clearTimeout(t);
  }, [dossier, search]);

  if (error) {
    return (
      <div className="fiche-page">
        <div className="fiche-page__chrome">
          <strong>Erreur :</strong> {error}
        </div>
      </div>
    );
  }
  if (!dossier) {
    return (
      <div className="fiche-page">
        <div className="fiche-page__chrome">Chargement de la fiche…</div>
      </div>
    );
  }

  const signatureUrl = dossier.donnees_pro?.extra?.signature_url || null;
  const imprimePar = me?.name || me?.email || "—";

  return (
    <div className="fiche-page">
      <div className="fiche-page__chrome">
        <a href={`/dossiers/${params.id}`} className="sa-btn sa-btn--ghost sa-btn--sm">
          ← Retour au dossier
        </a>
        <button
          type="button"
          className="sa-btn sa-btn--primary"
          onClick={() => window.print()}
        >
          🖨️ Imprimer
        </button>
      </div>
      <FicheInscription
        dossier={dossier}
        imprimePar={imprimePar}
        signatureUrl={signatureUrl}
      />
    </div>
  );
}
