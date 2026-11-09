"use client";
import { useId, useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";
import { Modal, PageHeader, Spinner } from "@/components/ui";

type MfaStatus = { enabled: boolean; enrolled_at: string | null };
type SetupPayload = {
  secret: string;
  otpauth_url: string;
  qr_code_data_uri: string;
  issuer: string;
};

export default function MfaPage() {
  const toast = useToast();
  const { data: status, loading, refetch } = useApi<MfaStatus>(() => api.mfaStatus());

  const [setup, setSetup] = useState<SetupPayload | null>(null);
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [disableOpen, setDisableOpen] = useState(false);

  async function startSetup() {
    setCode("");
    try {
      setSetup(await api.mfaSetup());
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  async function confirmEnable() {
    if (code.length !== 6) return;
    setSubmitting(true);
    try {
      await api.mfaEnable(code);
      toast({ tone: "success", title: "MFA activé", message: "Votre compte est désormais protégé." });
      setSetup(null);
      setCode("");
      await refetch();
    } catch (e: any) {
      toast({ tone: "error", title: "Code invalide", message: e.message });
    } finally {
      setSubmitting(false);
    }
  }

  async function disableMfa(totp: string) {
    try {
      await api.mfaDisable(totp);
      toast({ tone: "info", title: "MFA désactivé", message: "Pensez à le réactiver dès que possible." });
      setDisableOpen(false);
      await refetch();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Mon compte"
        title="Double authentification (MFA)"
        subtitle={
          "Renforce la sécurité de votre compte en exigeant un code à 6 chiffres "
          + "généré par une application d'authentification."
        }
      />
      {loading && <LoadingPanel />}
      {!loading && status?.enabled && <EnabledPanel status={status} onDisable={() => setDisableOpen(true)} />}
      {!loading && !status?.enabled && setup && (
        <SetupPanel
          setup={setup}
          code={code}
          onCodeChange={setCode}
          submitting={submitting}
          onCancel={() => { setSetup(null); setCode(""); }}
          onConfirm={confirmEnable}
        />
      )}
      {!loading && !status?.enabled && !setup && <InvitePanel onStart={startSetup} />}

      <DisableModal open={disableOpen} onClose={() => setDisableOpen(false)} onSubmit={disableMfa} />
    </div>
  );
}

function LoadingPanel() {
  return (
    <section className="sa-card" aria-busy="true">
      <div className="py-8 flex flex-col items-center gap-3">
        <Spinner size={24} />
        <div className="sa-help">Chargement…</div>
      </div>
    </section>
  );
}

function EnabledPanel({ status, onDisable }: { status: MfaStatus; onDisable: () => void }) {
  const date = status.enrolled_at
    ? new Date(status.enrolled_at).toLocaleDateString("fr-FR", { dateStyle: "long" })
    : "—";
  return (
    <section className="sa-card" aria-label="MFA activé">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <span className="sa-icon-tile sa-icon-tile--ok" aria-hidden="true">
          <Icon name="checkmark-circle-02" className="i" />
        </span>
        <div>
          <h2 className="sa-card__title sa-card__title--sm" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            MFA activé <span className="sa-badge sa-badge--ok">Activé</span>
          </h2>
          <p className="sa-card__subtitle">
            Activé le {date}. À chaque connexion, vous devrez saisir le code à 6 chiffres de votre application.
          </p>
        </div>
      </div>
      <div className="sa-actions-ligne">
        <button type="button" className="sa-btn sa-btn--danger" onClick={onDisable}>
          <Icon name="cancel-circle" className="i" />
          Désactiver le MFA
        </button>
      </div>
    </section>
  );
}

function SetupPanel(props: {
  setup: SetupPayload;
  code: string;
  onCodeChange: (v: string) => void;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const { setup, code, onCodeChange, submitting, onCancel, onConfirm } = props;
  const uid = useId();
  return (
    <section className="sa-card" aria-label="Activation du MFA">
      <h2 className="sa-card__title sa-card__title--sm" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Icon name="shield-user" className="i" />
        Activation du MFA
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-[208px_minmax(0,1fr)] gap-6 items-start">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={setup.qr_code_data_uri}
          alt="QR code MFA à scanner avec votre application d'authentification"
          width={192}
          height={192}
          style={{ background: "#fff", padding: 8, border: "1px solid rgb(var(--color-border-default))", borderRadius: "var(--radius-sm)" }}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ol className="sa-body" style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            <li>
              Installez <strong>Google Authenticator</strong>, <strong>Authy</strong> ou{" "}
              <strong>Microsoft Authenticator</strong>.
            </li>
            <li>
              Scannez le QR code. Impossible de scanner ? Saisissez la clé manuellement :
              <div className="sa-mono" style={{ marginTop: 4, padding: "6px 10px", overflowWrap: "anywhere", border: "1px dashed rgb(var(--color-border-default))", borderRadius: "var(--radius-sm)", background: "rgb(var(--color-bg-surface-subtle))" }}>
                {setup.secret}
              </div>
            </li>
            <li>Saisissez le code à 6 chiffres affiché par l&apos;application.</li>
          </ol>
          <form
            className="sa-form-ligne"
            onSubmit={(e) => { e.preventDefault(); onConfirm(); }}
          >
            <div className="sa-field" style={{ maxWidth: 220 }}>
              <label className="sa-label" htmlFor={`${uid}-code`}>Code à 6 chiffres</label>
              <input
                id={`${uid}-code`}
                className="sa-input sa-mono"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(e) => onCodeChange(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                style={{ textAlign: "center", letterSpacing: "0.4em", fontSize: 18 }}
              />
            </div>
            <button
              type="submit" className="sa-btn sa-btn--primary"
              disabled={code.length !== 6 || submitting} aria-busy={submitting || undefined}
            >
              {submitting ? "Vérification…" : "Activer"}
            </button>
            <button type="button" className="sa-btn sa-btn--ghost" onClick={onCancel}>Annuler</button>
          </form>
        </div>
      </div>
    </section>
  );
}

function InvitePanel({ onStart }: { onStart: () => void }) {
  return (
    <section className="sa-card" aria-label="MFA non activé">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <span className="sa-icon-tile" aria-hidden="true"><Icon name="lock-key" className="i" /></span>
        <div>
          <h2 className="sa-card__title sa-card__title--sm" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            MFA non activé <span className="sa-badge sa-badge--neutral">Non activé</span>
          </h2>
          <p className="sa-card__subtitle">
            Le MFA réduit considérablement le risque de compromission de votre compte, même si
            votre mot de passe est volé. Fortement recommandé pour les rôles admin et super-admin.
          </p>
        </div>
      </div>
      <div className="sa-actions-ligne">
        <button type="button" className="sa-btn sa-btn--primary" onClick={onStart}>
          <Icon name="shield-user" className="i" />
          Activer le MFA
        </button>
      </div>
    </section>
  );
}

/** Confirmation de désactivation : explique le risque et demande un code TOTP valide. */
function DisableModal({ open, onClose, onSubmit }: {
  open: boolean; onClose: () => void; onSubmit: (code: string) => void | Promise<void>;
}) {
  const uid = useId();
  const [totp, setTotp] = useState("");
  const [busy, setBusy] = useState(false);

  function close() { setTotp(""); onClose(); }
  async function submit() {
    if (!totp) return;
    setBusy(true);
    try { await onSubmit(totp); setTotp(""); } finally { setBusy(false); }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Désactiver le MFA ?"
      size="sm"
      footer={<>
        <button type="button" className="sa-btn sa-btn--ghost" onClick={close}>Annuler</button>
        <button
          type="submit" form={`${uid}-form`} className="sa-btn sa-btn--danger"
          disabled={totp.length < 6 || busy} aria-busy={busy || undefined}
        >
          Désactiver
        </button>
      </>}
    >
      <form
        id={`${uid}-form`}
        onSubmit={(e) => { e.preventDefault(); void submit(); }}
        style={{ display: "flex", flexDirection: "column", gap: 12 }}
      >
        <p className="sa-body" style={{ margin: 0 }}>
          Votre compte ne sera plus protégé par la double authentification. Saisissez un code TOTP
          valide à 6 chiffres pour confirmer.
        </p>
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-c`}>Code TOTP</label>
          <input
            id={`${uid}-c`} className="sa-input sa-mono" type="text" inputMode="numeric"
            autoComplete="one-time-code" maxLength={6} value={totp} placeholder="123456"
            onChange={(e) => setTotp(e.target.value.replace(/\D/g, ""))}
          />
        </div>
      </form>
    </Modal>
  );
}
