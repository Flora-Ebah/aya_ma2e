"use client";
import { useId, useState } from "react";
import { Modal } from "@/components/ui";
import type { User } from "./_types";

type Props = {
  open: boolean;
  user: User | null;
  onClose: () => void;
  onSubmit: (newPassword: string) => void;
};

export default function ResetPasswordModal({ open, user, onClose, onSubmit }: Props) {
  const uid = useId();
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const mismatch = confirm.length > 0 && pw !== confirm;
  const valid = pw.length >= 8 && pw === confirm;

  if (!user) return null;
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Réinitialiser le mot de passe"
      subtitle={`${user.name} · ${user.email}`}
      footer={<>
        <button type="button" className="sa-btn sa-btn--ghost" onClick={onClose}>Annuler</button>
        <button type="submit" form={`${uid}-form`} className="sa-btn sa-btn--primary" disabled={!valid}>
          Réinitialiser
        </button>
      </>}
    >
      <form
        id={`${uid}-form`}
        onSubmit={(e) => { e.preventDefault(); if (valid) onSubmit(pw); }}
        style={{ display: "flex", flexDirection: "column", gap: 16 }}
      >
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-pw`}>Nouveau mot de passe</label>
          <input
            id={`${uid}-pw`} className="sa-input" type="password" autoComplete="new-password"
            value={pw} onChange={(e) => setPw(e.target.value)} aria-describedby={`${uid}-pw-h`}
          />
          <div className="sa-help" id={`${uid}-pw-h`}>8 caractères minimum.</div>
        </div>
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-c`}>Confirmer</label>
          <input
            id={`${uid}-c`} className="sa-input" type="password" autoComplete="new-password"
            value={confirm} onChange={(e) => setConfirm(e.target.value)}
            aria-invalid={mismatch || undefined} aria-describedby={mismatch ? `${uid}-c-e` : undefined}
          />
          {mismatch && (
            <div className="sa-msg sa-msg--error" id={`${uid}-c-e`} role="alert">
              Les deux mots de passe ne correspondent pas.
            </div>
          )}
        </div>
      </form>
    </Modal>
  );
}
