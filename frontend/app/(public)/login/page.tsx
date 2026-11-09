"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/components/CurrentUserProvider";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import LoginForm from "./_LoginForm";
import MfaForm from "./_MfaForm";
import MarketingPanel from "./_MarketingPanel";

export default function LoginPage() {
  const router = useRouter();
  const { refresh: refreshCurrentUser } = useCurrentUser();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);

  // MFA challenge state (défini si le backend a demandé un 2e facteur)
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  // Redirection ?expired=1 depuis lib/api.ts (session expirée)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("expired") === "1") {
      setSessionExpired(true);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  async function finalizeLogin(_user: unknown) {
    // Le cookie httpOnly est déjà posé par le backend. On hydrate le
    // contexte React (en mémoire, jamais en localStorage) puis on route.
    await refreshCurrentUser();
    router.replace("/dossiers");
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await api.login(email, password);
      if (resp?.mfa_required) {
        setChallengeToken(resp.challenge_token);
        setMfaCode("");
      } else {
        finalizeLogin(resp.user);
      }
    } catch (e: any) {
      setError(
        e?.message?.includes("429")
          ? "Compte verrouillé temporairement."
          : "Identifiants invalides.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function onSubmitMfa(e: React.FormEvent) {
    e.preventDefault();
    if (!challengeToken) return;
    setError(null);
    setLoading(true);
    try {
      const resp = await api.mfaVerify(challengeToken, mfaCode);
      finalizeLogin(resp.user);
    } catch {
      setError("Code MFA invalide ou expiré.");
    } finally {
      setLoading(false);
    }
  }

  async function onAdLogin() {
    if (!email.trim()) {
      setError("Saisissez d'abord votre email ERANOVE pour vous connecter.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const resp = await api.adLogin(email.trim());
      if (resp?.mfa_required) {
        setChallengeToken(resp.challenge_token);
        setMfaCode("");
      } else {
        finalizeLogin(resp.user);
      }
    } catch (e: any) {
      setError(
        e?.message?.includes("400")
          ? "Email hors périmètre AD ERANOVE ou compte non configuré."
          : "Authentification AD impossible. Contactez votre administrateur.",
      );
    } finally {
      setLoading(false);
    }
  }

  function cancelMfa() {
    setChallengeToken(null);
    setMfaCode("");
    setError(null);
  }

  return (
    <div className="sa-auth">
      <MarketingPanel />
      <main className="sa-auth__main" id="contenu" tabIndex={-1}>
        <div className="sa-auth__logo">
          <Logo size={44} />
        </div>
        <div className="sa-auth__card">
          <div className="sa-auth__heading">
            <h1 className="sa-auth__title" id="titre-page">
              {challengeToken ? "Vérification en 2 étapes" : "Connexion à MA2E"}
            </h1>
            <p className="sa-auth__subtitle">
              {challengeToken ? "Un second facteur protège votre compte." : "Accédez à la console d’identification des sociétaires."}
            </p>
          </div>

          {!challengeToken ? (
            <LoginForm
              email={email} password={password}
              remember={remember} loading={loading}
              error={error} sessionExpired={sessionExpired}
              onEmailChange={setEmail} onPasswordChange={setPassword}
              onRememberChange={setRemember}
              onSubmit={onSubmit} onAdLogin={onAdLogin}
            />
          ) : (
            <MfaForm
              code={mfaCode} loading={loading} error={error}
              onCodeChange={setMfaCode}
              onSubmit={onSubmitMfa} onCancel={cancelMfa}
            />
          )}

          <div className="sa-auth__row">
            <span className="sa-body-sm sa-text-soft">Thème</span>
            <ThemeToggle />
          </div>
        </div>
        <p className="sa-body-sm sa-text-soft" style={{ textAlign: "center" }}>
          Plateforme sécurisée · Conforme loi 2013-450 (ARTCI)
        </p>
      </main>
    </div>
  );
}
