"use client";
import { createContext, forwardRef, useContext, useId } from "react";
import type {
  FormHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

/* -------------------------------------------------------------------------- */
/* Field : label + contrôle + aide / erreur, reliés par aria-describedby       */
/* -------------------------------------------------------------------------- */

type FieldCtx = { id: string; describedBy?: string; invalid: boolean; required: boolean };
const FieldContext = createContext<FieldCtx | null>(null);

type FieldProps = {
  label?: ReactNode;
  /** Aide sous le champ (ne décale pas les voisins : `align-items:start`). */
  help?: ReactNode;
  /** Message d'erreur : icône + texte, `aria-invalid` posé sur le contrôle. */
  error?: ReactNode;
  required?: boolean;
  /** Mention « facultatif » à droite du label. */
  optional?: boolean;
  /** Occupe toute la ligne d'un `FormGrid` (champ long, textarea). */
  full?: boolean;
  /** Identifiant du contrôle (sinon généré). */
  id?: string;
  className?: string;
  children: ReactNode;
};

/**
 * Champ de formulaire. Les contrôles enfants (`Input`, `Select`, `Textarea`,
 * `FileInput`, `SearchInput`) héritent de l'id, de `aria-invalid` et de
 * `aria-describedby`.
 *
 *   <Field label="Matricule" required help="8 chiffres" error={errors.matricule}>
 *     <Input value={v} onChange={…} />
 *   </Field>
 */
export function Field({ label, help, error, required, optional, full, id, className, children }: FieldProps) {
  const auto = useId();
  const fid = id ?? `f${auto.replace(/:/g, "")}`;
  const msgId = `${fid}-msg`;
  const hasMsg = Boolean(error || help);
  return (
    <FieldContext.Provider value={{ id: fid, describedBy: hasMsg ? msgId : undefined, invalid: Boolean(error), required: Boolean(required) }}>
      <div className={cx("sa-field", full && "sa-field--full", className)}>
        {label !== undefined && label !== null && label !== "" && (
          <div className={optional ? "sa-label-row" : undefined}>
            <label className="sa-label" htmlFor={fid}>
              {label}
              {required && (
                <span className="sa-req" aria-hidden="true">
                  {" "}*
                </span>
              )}
            </label>
            {optional && <span className="sa-label__opt">facultatif</span>}
          </div>
        )}
        {children}
        {hasMsg &&
          (error ? (
            <div className="sa-msg sa-msg--error" id={msgId} role="alert">
              <Icon name="alert-circle" />
              <span>{error}</span>
            </div>
          ) : (
            <div className="sa-help" id={msgId}>
              {help}
            </div>
          ))}
      </div>
    </FieldContext.Provider>
  );
}

function useFieldProps<T extends { id?: string; "aria-describedby"?: string; "aria-invalid"?: boolean | "true" | "false" | "grammar" | "spelling" }>(props: T) {
  const ctx = useContext(FieldContext);
  return {
    id: props.id ?? ctx?.id,
    "aria-describedby": props["aria-describedby"] ?? ctx?.describedBy,
    "aria-invalid": props["aria-invalid"] ?? (ctx?.invalid ? true : undefined),
  };
}

/* -------------------------------------------------------------------------- */
/* Contrôles                                                                   */
/* -------------------------------------------------------------------------- */

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  /** Police mono (identifiants, références). */
  mono?: boolean;
  /** Callback simplifié recevant directement la valeur. */
  onValueChange?: (v: string) => void;
};

/** Champ texte 44 px. Hérite de `Field`. */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, mono, onValueChange, onChange, ...props },
  ref,
) {
  const a = useFieldProps(props);
  return (
    <input
      ref={ref}
      {...props}
      {...a}
      className={cx("sa-input", mono && "sa-mono", className)}
      onChange={(e) => {
        onChange?.(e);
        onValueChange?.(e.target.value);
      }}
    />
  );
});

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { onValueChange?: (v: string) => void };

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, onValueChange, onChange, children, ...props },
  ref,
) {
  const a = useFieldProps(props);
  return (
    <select
      ref={ref}
      {...props}
      {...a}
      className={cx("sa-select", className)}
      onChange={(e) => {
        onChange?.(e);
        onValueChange?.(e.target.value);
      }}
    >
      {children}
    </select>
  );
});

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { onValueChange?: (v: string) => void };

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, onValueChange, onChange, rows = 4, ...props },
  ref,
) {
  const a = useFieldProps(props);
  return (
    <textarea
      ref={ref}
      rows={rows}
      {...props}
      {...a}
      className={cx("sa-textarea", className)}
      onChange={(e) => {
        onChange?.(e);
        onValueChange?.(e.target.value);
      }}
    />
  );
});

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: ReactNode;
  /** Texte d'aide sous le libellé. */
  description?: ReactNode;
  radio?: boolean;
  onCheckedChange?: (v: boolean) => void;
};

/** Case à cocher (ou radio) 44 px de haut avec libellé cliquable. */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, description, radio, className, onCheckedChange, onChange, ...props },
  ref,
) {
  return (
    <label className={cx("sa-check", !!description && "sa-check--top", className)}>
      <input
        ref={ref}
        type={radio ? "radio" : "checkbox"}
        {...props}
        onChange={(e) => {
          onChange?.(e);
          onCheckedChange?.(e.target.checked);
        }}
      />
      <span className="sa-check__text">
        {label}
        {description && <span className="sa-check__desc"> {description}</span>}
      </span>
    </label>
  );
});

type SwitchProps = {
  checked: boolean;
  onChange: (v: boolean) => void;
  /** Libellé visible à droite (sinon fournir `aria-label`). */
  label?: ReactNode;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
  className?: string;
};

/** Interrupteur 48×28 (`role="switch"`). */
export function Switch({ checked, onChange, label, disabled, id, className, ...rest }: SwitchProps) {
  const auto = useId();
  const sid = id ?? `sw${auto.replace(/:/g, "")}`;
  return (
    <span className={cx("sa-switch-row", className)}>
      <button
        type="button"
        role="switch"
        id={sid}
        className="sa-switch"
        aria-checked={checked}
        aria-label={rest["aria-label"]}
        aria-labelledby={label ? `${sid}-l` : undefined}
        disabled={disabled}
        onClick={() => onChange(!checked)}
      />
      {label && (
        <label id={`${sid}-l`} htmlFor={sid} className="sa-body">
          {label}
        </label>
      )}
    </span>
  );
}

type FileInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value"> & {
  /** Texte d'aide dans la zone de dépôt (ex. « PDF, 10 Mo max »). */
  hint?: ReactNode;
  title?: string;
  onFiles?: (files: FileList | null) => void;
};

/** Zone de dépôt + sélection de fichier (input natif accessible). */
export const FileInput = forwardRef<HTMLInputElement, FileInputProps>(function FileInput(
  { hint, title = "Glissez un fichier ou cliquez pour parcourir", onFiles, onChange, className, ...props },
  ref,
) {
  const a = useFieldProps(props);
  return (
    <label className={cx("sa-dropzone", className)} htmlFor={a.id}>
      <Icon name="upload-02" size={28} />
      <span className="sa-dropzone__title">{title}</span>
      {hint && <span className="sa-dropzone__hint">{hint}</span>}
      <input
        ref={ref}
        type="file"
        className="sa-sr-only"
        {...props}
        {...a}
        onChange={(e) => {
          onChange?.(e);
          onFiles?.(e.target.files);
        }}
      />
    </label>
  );
});

type SearchInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { onValueChange?: (v: string) => void };

/** Champ de recherche avec loupe (`sa-input-group`). */
export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(function SearchInput(
  { className, placeholder = "Rechercher…", onValueChange, onChange, "aria-label": ariaLabel, ...props },
  ref,
) {
  return (
    <div className={cx("sa-input-group", className)}>
      <Icon name="search-01" />
      <input
        ref={ref}
        type="search"
        autoComplete="off"
        className="sa-input"
        placeholder={placeholder}
        aria-label={ariaLabel ?? (typeof placeholder === "string" ? placeholder : "Rechercher")}
        {...props}
        onChange={(e) => {
          onChange?.(e);
          onValueChange?.(e.target.value);
        }}
      />
    </div>
  );
});

/* -------------------------------------------------------------------------- */
/* Mise en page des formulaires                                                */
/* -------------------------------------------------------------------------- */

type FormGridProps = FormHTMLAttributes<HTMLFormElement> & { as?: "form" | "div" };

/**
 * Grille de formulaire : 3 colonnes dès 1280 px, 2 de 768 à 1279, 1 en mobile.
 * Un champ seul / long : `<Field full>`. Textarea = pleine largeur automatiquement.
 */
export function FormGrid({ as = "div", className, children, ...rest }: FormGridProps) {
  const cls = cx("sa-grid sa-form-grid", className);
  if (as === "form") {
    return (
      <form className={cls} {...rest}>
        {children}
      </form>
    );
  }
  return <div className={cls}>{children}</div>;
}

/** Boutons d'un formulaire sur une ligne (un seul primaire). `sticky` : barre collée en bas. */
export function FormActions({ children, sticky, className, align = "start" }: { children: ReactNode; sticky?: boolean; className?: string; align?: "start" | "end" }) {
  return (
    <div className={cx("sa-form-actions", sticky && "sa-form-actions--sticky", className)} style={align === "end" ? { justifyContent: "flex-end" } : undefined}>
      {children}
    </div>
  );
}
