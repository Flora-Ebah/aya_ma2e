import { Grid, KpiCard } from "@/components/ui";
import type { Stats } from "./_types";

type Props = {
  stats: Stats;
  /** Statut actuellement filtré ("" = tous). */
  activeStatus: string;
  /** Clic sur une carte → filtre la liste sur ce statut. */
  onSelect: (status: string) => void;
};

const CARDS: { key: string; label: string; icon: string; hint: string; tone: "neutre" | "marque" | "ok" | "warn" | "error" | "info" }[] = [
  { key: "", label: "Total des dossiers", icon: "folder-01", hint: "Tous statuts confondus", tone: "marque" },
  { key: "soumis", label: "Soumis", icon: "task-01", hint: "En attente de prise en charge", tone: "info" },
  { key: "en_validation", label: "En validation", icon: "hourglass", hint: "Pris en charge par un gestionnaire", tone: "warn" },
  { key: "valide", label: "Validés", icon: "checkmark-circle-02", hint: "Sociétaires enrôlés", tone: "ok" },
  { key: "rejete", label: "Rejetés", icon: "cancel-circle", hint: "Dossiers refusés", tone: "error" },
  { key: "complement_requis", label: "Complément requis", icon: "alert-circle", hint: "En attente du sociétaire", tone: "warn" },
];

/**
 * Statistiques en cartes cliquables (3 par ligne, hauteur égale) : un clic
 * filtre la liste sur le statut correspondant.
 */
export default function StatsHeader({ stats, activeStatus, onSelect }: Props) {
  return (
    <div style={{ marginBottom: "var(--spacing-6)" }} role="group" aria-label="Filtrer par statut">
      <Grid variant="stats3">
        {CARDS.map((c) => {
          const value = c.key === "" ? stats.total : stats.by_status[c.key] ?? 0;
          return (
            <KpiCard
              key={c.key || "all"}
              label={c.label}
              value={value.toLocaleString("fr-FR")}
              icon={c.icon}
              iconTone={c.tone}
              meta={c.hint}
              active={activeStatus === c.key}
              onClick={() => onSelect(c.key)}
            />
          );
        })}
      </Grid>
    </div>
  );
}
