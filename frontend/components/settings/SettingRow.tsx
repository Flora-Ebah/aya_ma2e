"use client";
import type { ReactNode } from "react";
import { useId } from "react";

/** Structure d'un paramètre côté API (catégorie + méta pour rendu). */
export type SettingValue = {
  category: string;
  key: string;
  value: any;
  value_type: "string" | "text" | "integer" | "boolean" | "float" | "enum" | "json";
  version: number;
  is_default: boolean;
  updated_at: string | null;
  updated_by?: string | null;
  label: string;
  description: string;
  enum_options: string[] | null;
  min_value: number | null;
  max_value: number | null;
  max_length: number | null;
  sensitive?: boolean;
  group: string;
};

type Props = {
  setting: SettingValue;
  draft: any;
  onChange: (v: any) => void;
  onSave: () => void;
  saving: boolean;
  dirty: boolean;
};

/**
 * Carte d'édition d'un paramètre applicatif (design system GS2E).
 *
 * Libellé, aide sous le champ, code technique (mono), contrôle adapté au
 * type (interrupteur `sa-switch` pour les booléens) et bouton « Enregistrer »
 * sur une ligne. À placer dans un `SettingsGroup` / `SettingsGrid` : 2 cartes
 * par ligne dès 1024 px, les paramètres de type « text » occupent toute la ligne.
 *
 * Partagé entre `/parametres/general`, `/administration/securite`,
 * `/administration/integrations`, `/assistante/personnalite`, etc.
 */
export function SettingRow({ setting, draft, onChange, onSave, saving, dirty }: Props) {
  const id = useId();
  const isText = setting.value_type === "text";
  const isBool = setting.value_type === "boolean";
  const hintId = `${id}-hint`;
  const labelId = `${id}-label`;

  return (
    <div
      className={`sa-card ${isText ? "lg:col-span-2" : ""}`}
      style={{ height: "100%", gap: 12 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <label htmlFor={isBool ? undefined : id} id={labelId} className="sa-label">
            {setting.label}
          </label>
          <div className="sa-help" id={hintId} style={{ marginTop: 2 }}>
            {setting.description}
          </div>
        </div>
        {isBool && (
          <SettingSwitch checked={Boolean(draft)} onChange={onChange} labelledBy={labelId} describedBy={hintId} />
        )}
      </div>

      {!isBool && (
        <SettingInput id={id} describedBy={hintId} setting={setting} value={draft} onChange={onChange} />
      )}

      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          gap: 12, flexWrap: "wrap", marginTop: "auto",
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span className="sa-badge sa-badge--neutral sa-mono" title="Code technique">{setting.key}</span>
          <span className="sa-micro sa-text-soft">
            {setting.is_default ? "Valeur par défaut" : `v${setting.version}`}
          </span>
        </span>
        <button
          type="button"
          className="sa-btn sa-btn--primary sa-btn--sm"
          onClick={onSave}
          disabled={!dirty || saving}
          aria-busy={saving || undefined}
        >
          {saving ? "Enregistrement…" : "Enregistrer"}
        </button>
      </div>
    </div>
  );
}

/** Interrupteur accessible (rôle switch) qui affiche son état en texte. */
export function SettingSwitch({ checked, onChange, labelledBy, describedBy }: {
  checked: boolean; onChange: (v: boolean) => void; labelledBy?: string; describedBy?: string;
}) {
  return (
    <span className="sa-switch-row" style={{ flex: "none" }}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        className="sa-switch"
        onClick={() => onChange(!checked)}
      />
      <span className="sa-micro" style={{ minWidth: 76 }}>{checked ? "ACTIVÉ" : "DÉSACTIVÉ"}</span>
    </span>
  );
}

/**
 * Grille de cartes de paramètres : 1 colonne sur mobile, 2 dès 1024 px,
 * cartes de même hauteur, jamais d'orpheline (la dernière carte impaire
 * s'étend sur toute la ligne).
 */
export function SettingsGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch lg:[&>:last-child:nth-child(odd)]:col-span-2">
      {children}
    </div>
  );
}

/** Groupe de paramètres : titre de section + grille de cartes. */
export function SettingsGroup({ title, icon, children }: {
  title: string; icon?: ReactNode; children: ReactNode;
}) {
  return (
    <section style={{ marginBottom: 24 }} aria-label={title}>
      <h2 className="sa-h4" style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 12px" }}>
        {icon}
        {title}
      </h2>
      <SettingsGrid>{children}</SettingsGrid>
    </section>
  );
}

/** Convertit la valeur brute saisie vers le bon type Python. */
export function coerceSettingValue(raw: any, type: SettingValue["value_type"]) {
  if (type === "integer") return parseInt(String(raw), 10);
  if (type === "float") return parseFloat(String(raw));
  if (type === "boolean") return Boolean(raw);
  return raw;
}

function SettingInput({ id, describedBy, setting, value, onChange }: {
  id: string; describedBy: string;
  setting: SettingValue; value: any; onChange: (v: any) => void;
}) {
  if (setting.value_type === "enum" && setting.enum_options) {
    return (
      <select
        id={id} aria-describedby={describedBy} className="sa-select" style={{ width: "100%" }}
        value={value ?? ""} onChange={(e) => onChange(e.target.value)}
      >
        {setting.enum_options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    );
  }
  if (setting.value_type === "integer" || setting.value_type === "float") {
    return (
      <input
        id={id} aria-describedby={describedBy} className="sa-input" style={{ width: "100%" }} type="number"
        value={value ?? ""} onChange={(e) => onChange(e.target.value)}
        min={setting.min_value ?? undefined} max={setting.max_value ?? undefined}
        step={setting.value_type === "integer" ? 1 : "any"}
      />
    );
  }
  if (setting.value_type === "text") {
    // Textarea multi-lignes (persona IA, longs libellés éditoriaux…)
    const rows = Math.max(6, Math.min(20, String(value ?? "").split("\n").length + 2));
    return (
      <div>
        <textarea
          id={id} aria-describedby={describedBy} className="sa-textarea sa-mono"
          value={value ?? ""} onChange={(e) => onChange(e.target.value)}
          rows={rows} maxLength={setting.max_length ?? undefined}
          style={{ width: "100%", lineHeight: 1.5 }}
        />
        {setting.max_length && (
          <div className="sa-micro sa-text-soft sa-mono" style={{ textAlign: "right", marginTop: 4 }}>
            {String(value ?? "").length} / {setting.max_length}
          </div>
        )}
      </div>
    );
  }
  return (
    <input
      id={id} aria-describedby={describedBy} className="sa-input" style={{ width: "100%" }}
      type={setting.sensitive ? "password" : "text"}
      value={value ?? ""} onChange={(e) => onChange(e.target.value)}
      maxLength={setting.max_length ?? undefined}
      autoComplete={setting.sensitive ? "new-password" : undefined}
    />
  );
}
