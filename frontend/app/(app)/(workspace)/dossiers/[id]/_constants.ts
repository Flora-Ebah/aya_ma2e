export const FIELD_LABELS: Record<string, string> = {
  numero_piece: "N° de pièce",
  nom: "Nom",
  prenoms: "Prénoms",
  sexe: "Sexe",
  date_naissance: "Date de naissance",
  lieu_naissance: "Lieu de naissance",
  nationalite: "Nationalité",
  date_delivrance: "Date de délivrance",
  date_expiration: "Date d'expiration",
  adresse: "Adresse",
  document_number: "N° document",
  document_type: "Type document",
  issuing_country: "Pays émetteur",
  date_naissance_iso: "Date de naissance",
  date_expiration_iso: "Date d'expiration",
};

/** Journal d'audit → libellé, icône HugeIcons et variante de pastille de la timeline. */
export const AUDIT_LABELS: Record<string, { label: string; icon: string; dot: string }> = {
  dossier_created: { label: "Dossier créé", icon: "file-01", dot: "create" },
  dossier_submitted: { label: "Dossier soumis", icon: "task-01", dot: "create" },
  dossier_validated: { label: "Dossier validé", icon: "checkmark-circle-02", dot: "done" },
  dossier_rejected: { label: "Dossier rejeté", icon: "cancel-circle", dot: "alert" },
  dossier_complement_requested: { label: "Complément / mise à jour demandé", icon: "alert-circle", dot: "warn" },
  piece_uploaded: { label: "Pièce téléversée", icon: "upload-02", dot: "ot" },
  piece_ocr_completed: { label: "OCR effectué", icon: "analytics-01", dot: "ot" },
  piece_viewed: { label: "Pièce consultée", icon: "view", dot: "" },
  consent_given: { label: "Consentement signé", icon: "signature", dot: "done" },
  consent_refused: { label: "Consentement refusé", icon: "cancel-circle", dot: "alert" },
  consent_revoked: { label: "Consentement révoqué", icon: "alert-02", dot: "alert" },
};

export const TOC = [
  { id: "vue-ensemble", label: "Vue d'ensemble" },
  { id: "societaire", label: "Sociétaire" },
  { id: "etat-civil", label: "État civil" },
  { id: "identite", label: "Identité officielle" },
  { id: "piece-decl", label: "Pièce déclarée" },
  { id: "profession", label: "Données professionnelles" },
  { id: "contacts", label: "Coordonnées de contact" },
  { id: "famille", label: "Famille & à prévenir" },
  { id: "rib", label: "Coordonnées bancaires" },
  { id: "consentements", label: "Consentements ARTCI" },
  { id: "audit", label: "Historique & audit" },
];

const SITUATION_LABELS: Record<string, string> = {
  celibataire: "Célibataire",
  marie: "Marié(e)",
  divorce: "Divorcé(e)",
  veuf: "Veuf / Veuve",
};

const PIECE_LABELS: Record<string, string> = {
  cni: "Carte Nationale d'Identité",
  cni_uemoa: "Carte Nationale d'Identité",
  passeport: "Passeport",
  attestation: "Attestation d'identité",
  carte_consulaire: "Carte Consulaire",
  carte_resident: "Carte de Résident",
};

export function prettifySituation(s?: string | null): string {
  if (!s) return "";
  return SITUATION_LABELS[s.toLowerCase()] || s;
}

export function prettifyPieceType(s?: string | null): string {
  if (!s) return "";
  return PIECE_LABELS[s.toLowerCase()] || s;
}

export function fmtDate(d?: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
}

export function fmtDateTime(d?: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
}

export function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const y = el.getBoundingClientRect().top + window.scrollY - 76;
  window.scrollTo({ top: y, behavior: "smooth" });
}
