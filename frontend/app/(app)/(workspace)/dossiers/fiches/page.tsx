"use client";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import FicheInscription from "../[id]/fiche/_FicheInscription";
import "../[id]/fiche/fiche.css";

/**
 * Impression groupée : /dossiers/fiches?ids=a,b,c
 * Charge tous les dossiers en parallèle et empile les fiches (page-break
 * automatique), puis window.print() si ?print=1.
 */
export default function BulkFichePage() {
  const search = useSearchParams();
  const ids = (search.get("ids") || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const [items, setItems] = useState<any[]>([]);
  const [me, setMe] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const printedRef = useRef(false);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [list, user] = await Promise.all([
          Promise.all(ids.map((id) => api.getDossier(id).catch(() => null))),
          api.me().catch(() => null),
        ]);
        if (cancel) return;
        setItems(list.filter(Boolean));
        setMe(user);
      } catch (e: any) {
        setError(e?.message || "Erreur de chargement.");
      }
    })();
    return () => {
      cancel = true;
    };
  }, [ids.join(",")]);

  useEffect(() => {
    if (!items.length || printedRef.current) return;
    if (search.get("print") !== "1") return;
    printedRef.current = true;
    const t = setTimeout(() => window.print(), 800);
    return () => clearTimeout(t);
  }, [items, search]);

  if (error) {
    return (
      <div className="fiche-page">
        <div className="fiche-page__chrome"><strong>Erreur :</strong> {error}</div>
      </div>
    );
  }
  if (!ids.length) {
    return (
      <div className="fiche-page">
        <div className="fiche-page__chrome">Aucun dossier sélectionné.</div>
      </div>
    );
  }

  const imprimePar = me?.name || me?.email || "—";

  return (
    <div className="fiche-page">
      <div className="fiche-page__chrome">
        <a href="/dossiers" className="sa-btn sa-btn--ghost sa-btn--sm">← Retour aux dossiers</a>
        <span>{items.length} / {ids.length} fiches chargées</span>
        <button
          type="button"
          className="sa-btn sa-btn--primary"
          onClick={() => window.print()}
          disabled={items.length === 0}
        >
          🖨️ Imprimer tout
        </button>
      </div>
      {items.map((d) => (
        <FicheInscription
          key={d.id}
          dossier={d}
          imprimePar={imprimePar}
          signatureUrl={d.donnees_pro?.extra?.signature_url || null}
        />
      ))}
    </div>
  );
}
