"use client";
import { useMemo } from "react";

/**
 * Fiche d'inscription MA2E — reproduction fidèle du PDF Perfect Vision :
 * - grille 4 colonnes (label-G | valeur-G | label-D | valeur-D)
 * - photo en cell qui spanne les rangs 2..6 des colonnes 3-4
 * - tous les labels fond lavande
 * - compact pour tenir sur 1 page A4
 */

type Dossier = any;

type Cell = { label: string; value: string };

export default function FicheInscription({
  dossier,
  imprimePar,
  signatureUrl,
}: {
  dossier: Dossier;
  imprimePar: string;
  signatureUrl?: string | null;
}) {
  const extra = dossier.donnees_pro?.extra || {};
  const d = dossier.donnees_pro || {};
  const end = dossier.end_user || {};

  const nomParts = (end.name || "").trim().split(/\s+/).filter(Boolean);
  const nom = nomParts.length > 0 ? nomParts[nomParts.length - 1] : "";
  const prenoms = nomParts.length > 1 ? nomParts.slice(0, -1).join(" ") : "";

  const consentOk = (dossier.consentements || []).some(
    (c: any) => c.decision === "accepte",
  );

  // Colonne gauche : 19 lignes exactement comme le PDF original.
  // Aucune valeur inventée : ce qu'on n'a pas en base reste vide (cellule nbsp).
  const left: Cell[] = [
    { label: "Code", value: dossier.numero_societaire || dossier.dossier_number || "" },
    { label: "Type client", value: extra.type_client || "" },
    { label: "Civilité", value: extra.civilite || "" },
    { label: "Nom", value: nom },
    { label: "Prénoms", value: prenoms },
    { label: "Situation matrimoniale", value: d.situation_familiale || "" },
    { label: "Date naissance", value: extra.date_naissance || "" },
    { label: "Lieu de naissance", value: extra.lieu_naissance || "" },
    { label: "Pièce d'identité", value: pieceLabel(extra.type_piece) },
    { label: "N° pièce", value: extra.numero_piece || "" },
    { label: "Domicile", value: extra.domicile || extra.adresse_domicile || "" },
    { label: "Boîte postale", value: extra.boite_postale_choisie || extra.boite_postale || "" },
    { label: "Téléphone", value: end.phone || "" },
    { label: "E-mail", value: end.extra?.email || "" },
    { label: "Situation géographique", value: extra.situation_geographique || "" },
    { label: "Distance agence", value: extra.distance_agence || "" },
    { label: "Profession", value: d.fonction || "" },
    { label: "Nom conjoint(e)", value: extra.nom_conjoint || "" },
    { label: "Nom pers. à prévenir", value: extra.personne_a_prevenir || "" },
  ];

  // Colonne droite : 1 ligne en haut, photo (5 lignes), puis 13 lignes
  // pour aligner avec la colonne gauche de 19 lignes au total.
  const rightTop: Cell = {
    label: "Numéro manuel",
    value: dossier.matricule || "",
  };
  const rightBottom: Cell[] = [
    { label: "Num compte", value: dossier.numero_compte || "" },
    { label: "Adr. pers. à prévenir", value: extra.contact_prevenir_1 || "" },
    { label: "Bénéficiaire", value: "" },
    { label: "Tuteur", value: "" },
    { label: "Ayant droit", value: extra.ayants_droit || "" },
    { label: "Nombre de signatures lors des retraits", value: extra.nombre_signatures || "" },
    { label: "Date inscription", value: dossier.created_at ? new Date(dossier.created_at).toLocaleDateString("fr-FR") : "" },
    { label: "Gestionnaire", value: dossier.gestionnaire_name || "" },
    { label: "Nom du tuteur", value: extra.nom_tuteur || "" },
    { label: "Observations", value: extra.observations || "" },
  ];

  const now = useMemo(() => new Date(), []);
  const imprimeLe = now
    .toLocaleString("fr-FR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    })
    .replace(",", "");
  const journee = now.toLocaleDateString("fr-FR");

  const recto = (dossier.pieces || []).find((p: any) => p.face === "recto");
  const photoUrl = recto?.storage_key?.startsWith("http") ? recto.storage_key : null;

  // Construction des 19 rangs : chacun = {gridRow: n}. Colonne gauche systématique.
  // Colonne droite : rang 1 = rightTop ; rangs 2..6 = photo (cell unique spanning
  // rows 2/7, cols 3/5) ; rangs 7..19 = rightBottom[0..12].

  return (
    <article className="fiche">
      <header className="fiche__head">
        <div>
          <div className="fiche__brand">MA2E</div>
          <div>Tel : 21-23-64-87</div>
          <div>BP : 1210 ABJ18</div>
        </div>
        <div className="fiche__head-right">
          <div>Imprimé le : {imprimeLe}</div>
          <div>Imprimé par : {imprimePar}</div>
          <div>Journée : {journee}</div>
        </div>
      </header>

      <div className="fiche__title-rule">
        <h1 className="fiche__title">FICHE D&apos;INSCRIPTION</h1>
      </div>

      <div className="fiche__grid">
        {/* Colonne gauche */}
        {left.map((c, i) => (
          <div key={`lL${i}`} className="fiche__label" style={{ gridColumn: 1, gridRow: i + 1 }}>
            {c.label}
          </div>
        ))}
        {left.map((c, i) => (
          <div key={`lV${i}`} className="fiche__value" style={{ gridColumn: 2, gridRow: i + 1 }}>
            {c.value || " "}
          </div>
        ))}

        {/* Rang 1 droite : Numéro manuel */}
        <div className="fiche__label" style={{ gridColumn: 3, gridRow: 1 }}>{rightTop.label}</div>
        <div className="fiche__value" style={{ gridColumn: 4, gridRow: 1 }}>{rightTop.value || " "}</div>

        {/* Photo : rows 2..6, cols 3..4 */}
        <div className="fiche__photo" style={{ gridColumn: "3 / span 2", gridRow: "2 / span 5" }}>
          <div className="fiche__photo-box">
            {photoUrl ? <img src={photoUrl} alt="" /> : null}
          </div>
          <div className="fiche__photo-label">Photo</div>
        </div>

        {/* Rangs 7..19 droite */}
        {rightBottom.map((c, i) => (
          <div key={`rL${i}`} className="fiche__label" style={{ gridColumn: 3, gridRow: 7 + i }}>
            {c.label}
          </div>
        ))}
        {rightBottom.map((c, i) => (
          <div key={`rV${i}`} className="fiche__value" style={{ gridColumn: 4, gridRow: 7 + i }}>
            {c.value || " "}
          </div>
        ))}
      </div>

      {/* Table Attribut / Valeur */}
      <table className="fiche__attrs">
        <thead>
          <tr>
            <th>Attribut</th>
            <th>Valeur</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>CATEGORIE</td><td>{extra.categorie || " "}</td></tr>
          <tr><td>EMPLOYEUR</td><td>{dossier.employeur_code || " "}</td></tr>
          <tr><td>CONSENTEMENT RECU</td><td>{consentOk ? "OUI" : "NON"}</td></tr>
          <tr><td>NOM DE MERE</td><td>{extra.nom_mere || " "}</td></tr>
        </tbody>
      </table>

      {/* Mandataires : bandeau pleine largeur */}
      <div className="fiche__mandataires">Mandataires</div>

      {/* VISA + signature */}
      <div className="fiche__visa">
        <div className="fiche__visa-box">
          <div className="fiche__visa-title">VISA</div>
          <div className="fiche__visa-sig" />
        </div>
        <div className="fiche__visa-box">
          <div className="fiche__visa-title">Date et signature du client</div>
          <div className="fiche__visa-sig">
            {signatureUrl && <img src={signatureUrl} alt="Signature client" />}
          </div>
        </div>
      </div>

      <footer className="fiche__foot">
        <span>Perfect Vision v5.7.1.5</span>
        <span>1/1</span>
      </footer>
    </article>
  );
}

function pieceLabel(t?: string): string {
  if (!t) return "";
  const low = t.toLowerCase();
  if (low.includes("cni") || low.includes("carte")) return "Carte d'identité nationale";
  if (low.includes("pass")) return "Passeport";
  if (low.includes("attest")) return "Attestation d'identité";
  return t;
}
