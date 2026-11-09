"use client";
import { type AdvancedFilters, SORT_OPTIONS } from "./_types";

type Props = {
  value: AdvancedFilters;
  onChange: (v: AdvancedFilters) => void;
  onApply: () => void;
  onReset: () => void;
};

const EMPLOYEURS = ["CIE", "SODECI", "SMB", "AD_ERANOVE"];

/** Filtres avancés : 3 champs par ligne dès 1280 px, 2 dès 768 px, 1 sur mobile. */
export default function AdvancedFiltersPanel({ value, onChange, onApply, onReset }: Props) {
  const update = (patch: Partial<AdvancedFilters>) => onChange({ ...value, ...patch });

  return (
    <div
      id="dossiers-filtres-avances"
      style={{
        padding: "var(--spacing-5)",
        background: "rgb(var(--color-bg-surface-subtle))",
        borderTop: "1px solid rgb(var(--color-border-subtle))",
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" style={{ alignItems: "start" }}>
        <div className="sa-field">
          <label className="sa-label" htmlFor="f-employeur">Employeur</label>
          <select
            id="f-employeur" className="sa-select" value={value.employeur_code}
            onChange={(e) => update({ employeur_code: e.target.value })}
          >
            <option value="">Tous</option>
            {EMPLOYEURS.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>

        <div className="sa-field">
          <label className="sa-label" htmlFor="f-agent">
            Agent assigné <span className="sa-label__opt">(UUID, facultatif)</span>
          </label>
          <input
            id="f-agent" type="text" className="sa-input sa-mono" value={value.agent_id}
            onChange={(e) => update({ agent_id: e.target.value })}
            placeholder="00000000-0000-…"
          />
        </div>

        <div className="sa-field">
          <label className="sa-label" htmlFor="f-sort">Tri</label>
          <select
            id="f-sort" className="sa-select" value={value.sort}
            onChange={(e) => update({ sort: e.target.value })}
          >
            {SORT_OPTIONS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>

        <div className="sa-field">
          <label className="sa-label" htmlFor="f-since">Créé depuis le</label>
          <input
            id="f-since" type="date" className="sa-input" value={value.since}
            onChange={(e) => update({ since: e.target.value })}
          />
        </div>

        <div className="sa-field">
          <label className="sa-label" htmlFor="f-until">Créé jusqu&apos;au</label>
          <input
            id="f-until" type="date" className="sa-input" value={value.until}
            onChange={(e) => update({ until: e.target.value })}
          />
        </div>

        <div className="sa-field" style={{ justifyContent: "flex-end", gap: 4 }}>
          <label className="sa-check">
            <input
              type="checkbox" checked={value.priority_only}
              onChange={(e) => update({ priority_only: e.target.checked })}
            />
            <span className="sa-check__text">Prioritaires uniquement</span>
          </label>
          <label className="sa-check">
            <input
              type="checkbox" checked={value.overdue_only}
              onChange={(e) => update({ overdue_only: e.target.checked })}
            />
            <span className="sa-check__text">En retard (&gt; 48 h)</span>
          </label>
        </div>
      </div>

      <div className="sa-form-actions" style={{ marginTop: "var(--spacing-5)", justifyContent: "flex-end" }}>
        <button type="button" className="sa-btn sa-btn--ghost" onClick={onReset}>Réinitialiser</button>
        <button type="button" className="sa-btn sa-btn--primary" onClick={onApply}>Appliquer les filtres</button>
      </div>
    </div>
  );
}
