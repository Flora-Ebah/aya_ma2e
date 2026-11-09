import { Icon } from "@/components/Icon";

type Schema = { modules: string[]; actions: string[] };

const MODULE_LABELS: Record<string, string> = {
  validation: "Validation",
  reporting: "Reporting",
  administration: "Administration",
  audit: "Audit",
  conformite: "Conformité",
};

const ACTION_LABELS: Record<string, string> = {
  read: "Lire",
  write: "Modifier",
  delete: "Supprimer",
  export: "Exporter",
};

type Props = {
  schema: Schema;
  permissions: Record<string, Record<string, boolean>>;
  /** Vue en lecture (rôles listés) ou édition (modale). */
  readOnly?: boolean;
  onToggle?: (module: string, action: string) => void;
  onToggleRow?: (module: string) => void;
};

/**
 * Matrice de permissions RBAC (modules × actions), compacte et sans défilement
 * horizontal. Chaque état est exprimé par une icône ET un texte (lecture
 * seule) ou par une case à cocher nommée (édition).
 */
export default function PermissionsMatrix({ schema, permissions, readOnly = false, onToggle, onToggleRow }: Props) {
  return (
    <div className="sa-table-wrap">
      <table className="sa-table sa-table--compact sa-table--matrice">
        <caption className="sa-sr-only">Permissions par module et par action</caption>
        <thead>
          <tr>
            <th scope="col">Module</th>
            {schema.actions.map((a) => (
              <th key={a} scope="col" className="is-num">{ACTION_LABELS[a] || a}</th>
            ))}
            {!readOnly && <th scope="col" className="is-num">Tout</th>}
          </tr>
        </thead>
        <tbody>
          {schema.modules.map((m) => (
            <MatrixRow
              key={m}
              module={m}
              actions={schema.actions}
              permissions={permissions}
              readOnly={readOnly}
              onToggle={onToggle}
              onToggleRow={onToggleRow}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MatrixRow({ module, actions, permissions, readOnly, onToggle, onToggleRow }: {
  module: string;
  actions: string[];
  permissions: Record<string, Record<string, boolean>>;
  readOnly?: boolean;
  onToggle?: (m: string, a: string) => void;
  onToggleRow?: (m: string) => void;
}) {
  const allOn = actions.every((a) => permissions[module]?.[a]);
  const moduleLabel = MODULE_LABELS[module] || module;
  return (
    <tr>
      <th scope="row" style={{ fontWeight: 500, textAlign: "left" }}>{moduleLabel}</th>
      {actions.map((a) => {
        const on = Boolean(permissions[module]?.[a]);
        const actionLabel = ACTION_LABELS[a] || a;
        return (
          <td key={a} className="is-num">
            {readOnly ? (
              <span className={`sa-badge ${on ? "sa-badge--ok" : "sa-badge--neutral"}`} style={{ minHeight: 24 }}>
                <Icon name={on ? "tick-02" : "minus-sign"} className="i" />
                <span className="sa-sr-only">{`${moduleLabel} : ${actionLabel} — ${on ? "autorisé" : "non autorisé"}`}</span>
                <span aria-hidden="true">{on ? "Oui" : "Non"}</span>
              </span>
            ) : (
              <label className="sa-check" style={{ justifyContent: "center", minHeight: 36 }}>
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => onToggle?.(module, a)}
                  aria-label={`${moduleLabel} : ${actionLabel}`}
                />
              </label>
            )}
          </td>
        );
      })}
      {!readOnly && (
        <td className="is-num">
          <button
            type="button"
            className="sa-btn sa-btn--ghost sa-btn--sm"
            onClick={() => onToggleRow?.(module)}
            aria-label={`${allOn ? "Décocher" : "Cocher"} toutes les permissions du module ${moduleLabel}`}
          >
            {allOn ? "Vider" : "Tout"}
          </button>
        </td>
      )}
    </tr>
  );
}
