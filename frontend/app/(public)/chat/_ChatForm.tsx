"use client";
import { useMemo, useState } from "react";
import type { ChatFormField, ChatUiHint } from "./_utils";

type Props = {
  ui: ChatUiHint;
  disabled: boolean;
  onSubmit: (payload: string, displayText: string) => void;
  onEscape?: () => void;
};

/**
 * Rendu inline d'un formulaire envoyé par le bot :
 *   - type="form"   → tous les champs d'un step (select / text / email / tel / date)
 *   - type="select" → un seul choix (civilité, oui/non, catégorie, etc.)
 *
 * À la soumission, on compose un texte au format `Label: valeur` par ligne
 * (déjà compris par le backend via `_parse_form_response`) et un payload
 * lisible à afficher dans la bulle utilisateur.
 */
export default function ChatForm({ ui, disabled, onSubmit, onEscape }: Props) {
  if (ui.type === "signature") return null;
  const title =
    ui.type === "form"
      ? ui.title
      : ui.type === "select"
      ? ui.label
      : ui.title;
  const titleText = (title || "").trim();
  const descText = (ui.description || "").trim();

  return (
    <div className="chat-formcard">
      {titleText && (
        <div className="chat-formcard__title" aria-label="Étape en cours">
          {titleText}
        </div>
      )}
      {descText && (
        <div className="chat-formcard__desc">{descText}</div>
      )}
      {ui.type === "select" ? (
        <SelectBlock
          label={ui.label}
          options={ui.options}
          allowOther={!!ui.allow_other}
          disabled={disabled}
          onSubmit={(value) => onSubmit(value, value)}
        />
      ) : ui.type === "multi-select" ? (
        <MultiSelectBlock
          options={ui.options}
          min={ui.min || 1}
          max={ui.max || ui.options.length}
          disabled={disabled}
          onSubmit={(codes, labels) =>
            onSubmit(codes.join(","), `✔️ ${labels.join(" · ")}`)
          }
        />
      ) : ui.type === "form" ? (
        <FormBlock
          fields={ui.fields}
          disabled={disabled}
          onSubmit={(lines, display) => onSubmit(lines, display)}
        />
      ) : null}
      {onEscape && (
        <button
          type="button"
          className="chat-formcard__escape"
          onClick={onEscape}
          disabled={disabled}
        >
          Annuler et recommencer
        </button>
      )}
    </div>
  );
}

function SelectBlock({
  label, options, allowOther, disabled, onSubmit,
}: {
  label: string;
  options: { code: string; label: string }[];
  allowOther: boolean;
  disabled: boolean;
  onSubmit: (value: string) => void;
}) {
  const [other, setOther] = useState("");
  return (
    <div className="chat-form" role="group" aria-label={label || "Choix"}>
      <div className="chat-form__options">
        {options.map((opt) => (
          <button
            key={opt.code}
            type="button"
            className="chat-form__chip"
            disabled={disabled}
            onClick={() => onSubmit(opt.label)}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {allowOther && (
        <div className="chat-form__row chat-form__row--other">
          <input
            type="text"
            className="sa-input chat-form__input"
            placeholder="Autre (saisir)"
            value={other}
            disabled={disabled}
            onChange={(e) => setOther(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && other.trim()) onSubmit(other.trim());
            }}
          />
          <button
            type="button"
            className="sa-btn sa-btn--primary"
            disabled={disabled || !other.trim()}
            onClick={() => onSubmit(other.trim())}
          >
            Envoyer
          </button>
        </div>
      )}
    </div>
  );
}

function MultiSelectBlock({
  options, min, max, disabled, onSubmit,
}: {
  options: { code: string; label: string }[];
  min: number;
  max: number;
  disabled: boolean;
  onSubmit: (codes: string[], labels: string[]) => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  function toggle(code: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else if (next.size < max) next.add(code);
      return next;
    });
  }

  const count = selected.size;
  const canSubmit = count >= min && count <= max;

  function handleSubmit() {
    if (!canSubmit) return;
    const codes = options.filter((o) => selected.has(o.code)).map((o) => o.code);
    const labels = options.filter((o) => selected.has(o.code)).map((o) => o.label);
    onSubmit(codes, labels);
  }

  return (
    <div className="chat-multi">
      <div className="chat-multi__options">
        {options.map((opt) => {
          const on = selected.has(opt.code);
          return (
            <label key={opt.code} className={`chat-multi__opt${on ? " is-on" : ""}`}>
              <input
                type="checkbox"
                checked={on}
                disabled={disabled}
                onChange={() => toggle(opt.code)}
              />
              <span>{opt.label}</span>
            </label>
          );
        })}
      </div>
      <div className="chat-multi__foot">
        <span className="sa-text-soft" style={{ fontSize: 12 }}>
          {count} / {max} sélectionné{count > 1 ? "s" : ""}
          {min > 1 && count < min ? ` — minimum ${min}` : ""}
        </span>
        <button
          type="button"
          className="sa-btn sa-btn--primary"
          disabled={disabled || !canSubmit}
          onClick={handleSubmit}
        >
          Valider la sélection
        </button>
      </div>
    </div>
  );
}

function FormBlock({
  fields, disabled, onSubmit,
}: {
  fields: ChatFormField[];
  disabled: boolean;
  onSubmit: (lines: string, display: string) => void;
}) {
  const initial = useMemo(
    () => Object.fromEntries(fields.map((f) => [f.name, f.default || ""])),
    [fields],
  );
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const missing = fields
    .filter((f) => f.required !== false && !values[f.name]?.toString().trim())
    .map((f) => f.name);

  function handleChange(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit() {
    setTouched(Object.fromEntries(fields.map((f) => [f.name, true])));
    if (missing.length > 0) return;
    const lines = fields
      .map((f) => `${f.label}: ${(values[f.name] || "").toString().trim()}`)
      .join("\n");
    const summary = fields
      .filter((f) => (values[f.name] || "").toString().trim())
      .map((f) => `• ${f.label} : ${values[f.name]}`)
      .join("\n");
    const display = summary
      ? `*Réponses envoyées :*\n${summary}`
      : lines;
    onSubmit(lines, display);
  }

  return (
    <form
      className="chat-form"
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
      aria-label="Formulaire"
    >
      {fields.map((f) => {
        const err = touched[f.name] && f.required !== false && !values[f.name]?.toString().trim();
        return (
          <div key={f.name} className="chat-form__row">
            <label className="chat-form__label" htmlFor={`cf-${f.name}`}>
              {f.label}
              {f.required !== false && <span aria-hidden> *</span>}
            </label>
            {renderControl(f, values[f.name] || "", (v) => handleChange(f.name, v), disabled)}
            {err && <div className="chat-form__err">Ce champ est requis.</div>}
          </div>
        );
      })}
      <div className="chat-form__actions">
        <button
          type="submit"
          className="sa-btn sa-btn--primary"
          disabled={disabled || missing.length > 0}
        >
          Envoyer
        </button>
      </div>
    </form>
  );
}

function renderControl(
  f: ChatFormField,
  value: string,
  onChange: (v: string) => void,
  disabled: boolean,
) {
  const commonId = `cf-${f.name}`;
  if (f.type === "select" && f.options && f.options.length > 0) {
    return (
      <select
        id={commonId}
        className="sa-input chat-form__input"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">— Choisir —</option>
        {f.options.map((opt) => (
          <option key={opt.code} value={opt.label}>
            {opt.label}
          </option>
        ))}
        {f.allow_other && <option value="__other__">Autre…</option>}
      </select>
    );
  }
  const htmlType =
    f.type === "email" ? "email" :
    f.type === "tel" || f.type === "phone" ? "tel" :
    f.type === "date" ? "date" :
    f.type === "number" ? "number" :
    "text";
  return (
    <input
      id={commonId}
      type={htmlType}
      className="sa-input chat-form__input"
      value={value}
      placeholder={f.placeholder || ""}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
