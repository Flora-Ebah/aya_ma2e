export type Dossier = {
  id: string;
  dossier_number: string;
  numero_societaire?: string | null;
  status: string;
  matricule: string | null;
  employeur_code: string | null;
  end_user_name?: string | null;
  end_user_contact?: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at?: string | null;
  priority_review?: boolean;
  priority_reason?: string | null;
  locked?: boolean;
  locked_by?: string | null;
  locked_at?: string | null;
  age_hours?: number | null;
  is_overdue?: boolean;
};

export type Stats = { total: number; by_status: Record<string, number> };

/** Filtres avancés (US-38) — séparés du filtre statut pour permettre la combinaison. */
export type AdvancedFilters = {
  employeur_code: string;
  agent_id: string;
  priority_only: boolean;
  overdue_only: boolean;
  since: string;
  until: string;
  sort: string;
};

export const DEFAULT_ADVANCED: AdvancedFilters = {
  employeur_code: "",
  agent_id: "",
  priority_only: false,
  overdue_only: false,
  since: "",
  until: "",
  sort: "oldest_first",
};

export const STATUS_FILTERS = [
  { key: "", label: "Tous" },
  { key: "soumis", label: "Soumis" },
  { key: "en_validation", label: "En validation" },
  { key: "valide", label: "Validés" },
  { key: "rejete", label: "Rejetés" },
  { key: "complement_requis", label: "Complément" },
];

export const SORT_OPTIONS = [
  { key: "oldest_first", label: "Plus ancien d'abord (défaut)" },
  { key: "newest_first", label: "Plus récent d'abord" },
  { key: "priority", label: "Prioritaires en tête" },
  { key: "overdue", label: "En retard en tête" },
];

export function countActiveAdvanced(a: AdvancedFilters): number {
  let n = 0;
  if (a.employeur_code) n++;
  if (a.agent_id) n++;
  if (a.priority_only) n++;
  if (a.overdue_only) n++;
  if (a.since) n++;
  if (a.until) n++;
  if (a.sort && a.sort !== "oldest_first") n++;
  return n;
}
