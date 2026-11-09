"use client";
import { useId, useState } from "react";
import { Modal } from "@/components/ui";
import type { User } from "./_types";

type Payload = {
  email: string;
  name: string;
  role: User["role"];
  auth_method: "password" | "ad";
  password: string;
};

type Props = {
  open: boolean;
  isSuperAdmin: boolean;
  onClose: () => void;
  onSubmit: (p: Payload) => void;
};

/** Création d'un compte : petit formulaire, 3 champs par ligne, sans défilement. */
export default function CreateUserModal({ open, isSuperAdmin, onClose, onSubmit }: Props) {
  const uid = useId();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<User["role"]>("agent");
  const [authMethod, setAuthMethod] = useState<"password" | "ad">("password");
  const [password, setPassword] = useState("");

  const valid = email.trim() && name.trim() && (authMethod === "ad" || password.length >= 8);

  function submit() {
    if (!valid) return;
    onSubmit({
      email: email.trim(),
      name: name.trim(),
      role,
      auth_method: authMethod,
      password: authMethod === "ad" ? "" : password,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Nouvel utilisateur"
      size="xl"
      footer={<>
        <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
        <button type="submit" form={`${uid}-form`} className="sa-btn sa-btn--primary" disabled={!valid}>
          Créer le compte
        </button>
      </>}
    >
      <form
        id={`${uid}-form`}
        onSubmit={(e) => { e.preventDefault(); submit(); }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start"
      >
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-email`}>E-mail <span className="sa-req" aria-hidden="true">*</span></label>
          <input
            id={`${uid}-email`} className="sa-input" type="email" required autoComplete="off"
            value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jean.dupont@ma2e.ci"
          />
        </div>
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-name`}>Nom complet <span className="sa-req" aria-hidden="true">*</span></label>
          <input
            id={`${uid}-name`} className="sa-input" required autoComplete="off"
            value={name} onChange={(e) => setName(e.target.value)} placeholder="Jean Dupont"
          />
        </div>
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-role`}>Rôle système</label>
          <select
            id={`${uid}-role`} className="sa-select" value={role}
            onChange={(e) => setRole(e.target.value as User["role"])}
          >
            <option value="agent">Gestionnaire (validation des dossiers)</option>
            <option value="tenant_admin">Administrateur (gestion complète)</option>
            {isSuperAdmin && <option value="super_admin">Super-admin (accès complet)</option>}
          </select>
        </div>

        <fieldset className="sa-fieldset md:col-span-2" style={{ padding: 0, border: 0 }}>
          <legend className="sa-label" style={{ marginBottom: 6 }}>Mode d&apos;authentification</legend>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="sa-choice">
              <input type="radio" name={`${uid}-auth`} checked={authMethod === "password"} onChange={() => setAuthMethod("password")} />
              <span className="sa-choice__body">
                <span className="sa-choice__title">E-mail + mot de passe</span>
                <span className="sa-choice__desc">Compte local MA2E</span>
              </span>
            </label>
            <label className="sa-choice">
              <input type="radio" name={`${uid}-auth`} checked={authMethod === "ad"} onChange={() => setAuthMethod("ad")} />
              <span className="sa-choice__body">
                <span className="sa-choice__title">Active Directory</span>
                <span className="sa-choice__desc">Compte ERANOVE (SSO)</span>
              </span>
            </label>
          </div>
        </fieldset>

        {authMethod === "password" ? (
          <div className="sa-field">
            <label className="sa-label" htmlFor={`${uid}-pw`}>Mot de passe initial <span className="sa-req" aria-hidden="true">*</span></label>
            <input
              id={`${uid}-pw`} className="sa-input" type="password" autoComplete="new-password"
              value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby={`${uid}-pw-h`}
            />
            <div className="sa-help" id={`${uid}-pw-h`}>8 caractères minimum ; à changer à la première connexion.</div>
          </div>
        ) : (
          <div className="sa-help" style={{ alignSelf: "center" }}>
            Aucun mot de passe : l&apos;utilisateur se connecte avec ses identifiants groupe via le bouton « ERANOVE ».
          </div>
        )}
      </form>
    </Modal>
  );
}
