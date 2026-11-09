"use client";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";

type Props = {
  code: string;
  loading: boolean;
  error: string | null;
  onCodeChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
};

export default function MfaForm({ code, loading, error, onCodeChange, onSubmit, onCancel }: Props) {
  return (
    <form onSubmit={onSubmit} className="login-form">
      <p className="sa-body sa-text-soft">
        Saisissez le code à 6 chiffres affiché par votre application d&apos;authentification
        (Google Authenticator, Authy, etc.).
      </p>
      <Field label="Code à 6 chiffres" required>
        <Input
          type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
          value={code} placeholder="123456" autoFocus mono autoComplete="one-time-code"
          style={{ textAlign: "center", letterSpacing: "0.4em", fontSize: 22 }}
          onValueChange={(v) => onCodeChange(v.replace(/\D/g, ""))}
        />
      </Field>
      {error && <Alert tone="error" compact>{error}</Alert>}
      <Button type="submit" block loading={loading} disabled={code.length !== 6} icon="shield-user">
        {loading ? "Vérification…" : "Vérifier"}
      </Button>
      <Button type="button" variant="ghost" block onClick={onCancel}>
        Recommencer
      </Button>
    </form>
  );
}
