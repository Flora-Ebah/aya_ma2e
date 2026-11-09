import { STATUS_LABELS } from "@/lib/api";
import { Icon } from "@/components/Icon";

/** Statut → variante de badge + icône (icône + texte : jamais la couleur seule). */
const STATUS_META: Record<string, { tone: string; icon: string }> = {
  en_cours: { tone: "sa-badge--neutral", icon: "clock-01" },
  soumis: { tone: "sa-badge--info", icon: "task-01" },
  en_validation: { tone: "sa-badge--info", icon: "hourglass" },
  valide: { tone: "sa-badge--ok", icon: "checkmark-circle-02" },
  rejete: { tone: "sa-badge--error", icon: "cancel-circle" },
  complement_requis: { tone: "sa-badge--warn", icon: "alert-circle" },
};

export function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { tone: "sa-badge--neutral", icon: "file-01" };
  return (
    <span className={`sa-badge ${meta.tone}`}>
      <Icon name={meta.icon} className="i" />
      {STATUS_LABELS[status] || status}
    </span>
  );
}
