"use client";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Checkbox, Field, Input } from "@/components/ui/Field";

type Props = {
  email: string;
  password: string;
  remember: boolean;
  loading: boolean;
  error: string | null;
  sessionExpired: boolean;
  onEmailChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onRememberChange: (v: boolean) => void;
  onSubmit: (e: React.FormEvent) => void;
  onAdLogin: () => void;
};

export default function LoginForm({
  email, password, remember, loading, error, sessionExpired,
  onEmailChange, onPasswordChange, onRememberChange, onSubmit,
}: Props) {
  return (
    <form onSubmit={onSubmit} className="login-form" autoComplete="off">
      {/* Honeypots invisibles — Chrome/Edge ignorent souvent autoComplete="off"
          sur le vrai champ mais respectent l'absence d'attributs name standards
          si on leur donne d'abord 2 champs "appâts" cachés. */}
      <input type="text" name="prevent_autofill" tabIndex={-1} autoComplete="off" style={{ display: "none" }} />
      <input type="password" name="prevent_autofill_pwd" tabIndex={-1} autoComplete="new-password" style={{ display: "none" }} />

      <Field label="Adresse e-mail" required>
        <Input
          type="email" name="ma2e_login_email" value={email} required
          onValueChange={onEmailChange}
          autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
          data-form-type="other" data-lpignore="true" data-1p-ignore="true"
        />
      </Field>
      <Field label="Mot de passe" required>
        <Input
          type="password" name="ma2e_login_password" value={password} required
          onValueChange={onPasswordChange}
          autoComplete="new-password" autoCorrect="off" autoCapitalize="off" spellCheck={false}
          data-form-type="other" data-lpignore="true" data-1p-ignore="true"
        />
      </Field>

      <Checkbox label="Rester connecté" checked={remember} onCheckedChange={onRememberChange} />

      {sessionExpired && !error && <Alert tone="warning" compact>Votre session a expiré. Merci de vous reconnecter.</Alert>}
      {error && <Alert tone="error" compact>{error}</Alert>}

      <Button type="submit" block loading={loading} icon="login-02">
        {loading ? "Connexion…" : "Se connecter"}
      </Button>
    </form>
  );
}
