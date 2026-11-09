"use client";
import { useId, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useCurrentUser } from "@/components/CurrentUserProvider";
import { useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";
import { Modal, PageHeader, Spinner } from "@/components/ui";

type MfaStatus = { enabled: boolean; enrolled_at: string | null };

const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super-administrateur",
  tenant_admin: "Administrateur",
  agent: "Gestionnaire",
  viewer: "Consultation",
};

export default function ProfilPage() {
  const { user: me } = useCurrentUser();
  const { data: mfa, loading } = useApi<MfaStatus>(() => api.mfaStatus());

  return (
    <div>
      <PageHeader
        eyebrow="Mon compte"
        title="Mon profil"
        subtitle="Informations personnelles, mot de passe et double authentification."
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">
        <div className="lg:col-span-2">
          <IdentityCard user={me} />
        </div>
        <PasswordCard />
        {loading
          ? <section className="sa-card"><div className="py-6 flex justify-center"><Spinner /></div></section>
          : <MfaSummaryCard status={mfa} />}
      </div>
    </div>
  );
}

function IdentityCard({ user }: { user: any }) {
  const initial = (user?.name || "·").trim().charAt(0).toUpperCase();
  return (
    <section className="sa-card" aria-label="Identité">
      <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <span className="sa-avatar sa-avatar--48" aria-hidden="true">{initial}</span>
        <div style={{ minWidth: 0, flex: "1 1 220px" }}>
          <h2 className="sa-card__title">{user?.name || "—"}</h2>
          <div className="sa-mono sa-text-soft" style={{ overflowWrap: "anywhere" }}>{user?.email || ""}</div>
        </div>
        <dl style={{ display: "flex", gap: 32, flexWrap: "wrap", margin: 0 }}>
          <FieldRow label="Rôle système" value={ROLE_LABELS[user?.role] || user?.role || "—"} />
          <FieldRow label="Plateforme" value="MA2E" />
        </dl>
      </div>
    </section>
  );
}

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="sa-micro sa-text-soft">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600 }}>{value}</dd>
    </div>
  );
}

function PasswordCard() {
  const toast = useToast();
  const uid = useId();
  const [open, setOpen] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [saving, setSaving] = useState(false);

  const close = () => { setOpen(false); setCurrentPw(""); setNewPw(""); setConfirmPw(""); };
  const canSubmit = Boolean(currentPw) && newPw.length >= 8 && newPw === confirmPw;
  const mismatch = confirmPw.length > 0 && newPw !== confirmPw;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) {
      toast({ tone: "error", title: "Vérification", message: "Mots de passe différents ou trop courts." });
      return;
    }
    setSaving(true);
    try {
      await api.changeMyPassword(currentPw, newPw);
      toast({ tone: "success", title: "Mot de passe modifié", message: "Pensez à le mémoriser." });
      close();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <section className="sa-card" aria-label="Mot de passe" style={{ height: "100%" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <span className="sa-icon-tile" aria-hidden="true"><Icon name="lock-password" className="i" /></span>
          <div>
            <h2 className="sa-card__title sa-card__title--sm">Mot de passe</h2>
            <p className="sa-card__subtitle">
              Politique MA2E : 12 caractères minimum, 1 majuscule, 1 chiffre, 1 caractère spécial.
            </p>
          </div>
        </div>
        <div className="sa-actions-ligne" style={{ marginTop: "auto" }}>
          <button type="button" className="sa-btn sa-btn--outline" onClick={() => setOpen(true)}>
            <Icon name="edit-02" className="i" />
            Modifier le mot de passe
          </button>
        </div>
      </section>

      <Modal
        open={open}
        onClose={close}
        title="Modifier le mot de passe"
        size="sm"
        footer={<>
          <button type="button" className="sa-btn sa-btn--ghost" onClick={close}>Annuler</button>
          <button
            type="submit" form={`${uid}-form`} className="sa-btn sa-btn--primary"
            disabled={!canSubmit || saving} aria-busy={saving || undefined}
          >
            {saving ? "Enregistrement…" : "Modifier"}
          </button>
        </>}
      >
        <form id={`${uid}-form`} onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="sa-field">
            <label className="sa-label" htmlFor={`${uid}-cur`}>Mot de passe actuel</label>
            <input id={`${uid}-cur`} className="sa-input" type="password" required autoComplete="current-password"
              value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} />
          </div>
          <div className="sa-field">
            <label className="sa-label" htmlFor={`${uid}-new`}>Nouveau mot de passe</label>
            <input id={`${uid}-new`} className="sa-input" type="password" required autoComplete="new-password"
              value={newPw} onChange={(e) => setNewPw(e.target.value)} />
          </div>
          <div className="sa-field">
            <label className="sa-label" htmlFor={`${uid}-conf`}>Confirmer</label>
            <input id={`${uid}-conf`} className="sa-input" type="password" required autoComplete="new-password"
              value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)}
              aria-invalid={mismatch || undefined} aria-describedby={mismatch ? `${uid}-err` : undefined} />
            {mismatch && (
              <div className="sa-msg sa-msg--error" id={`${uid}-err`} role="alert">
                Les deux mots de passe ne correspondent pas.
              </div>
            )}
          </div>
        </form>
      </Modal>
    </>
  );
}

function MfaSummaryCard({ status }: { status: MfaStatus | null }) {
  const enabled = status?.enabled === true;
  const date = status?.enrolled_at
    ? new Date(status.enrolled_at).toLocaleDateString("fr-FR", { dateStyle: "long" })
    : "—";
  return (
    <section className="sa-card" aria-label="Double authentification" style={{ height: "100%" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <span className={`sa-icon-tile ${enabled ? "sa-icon-tile--ok" : ""}`} aria-hidden="true">
          <Icon name={enabled ? "checkmark-circle-02" : "shield-user"} className="i" />
        </span>
        <div>
          <h2 className="sa-card__title sa-card__title--sm" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            Double authentification (MFA)
            <span className={`sa-badge ${enabled ? "sa-badge--ok" : "sa-badge--neutral"}`}>
              {enabled ? "Activée" : "Non activée"}
            </span>
          </h2>
          <p className="sa-card__subtitle">
            {enabled
              ? <>Activée le {date}. Un code à 6 chiffres est demandé à chaque connexion.</>
              : "Fortement recommandée pour les rôles administrateurs. Compatible Google Authenticator, Authy, Microsoft Authenticator."}
          </p>
        </div>
      </div>
      <div className="sa-actions-ligne" style={{ marginTop: "auto" }}>
        <Link href="/parametres/mfa" className="sa-btn sa-btn--outline">
          {enabled ? "Gérer le MFA" : "Configurer le MFA"}
          <Icon name="arrow-right-01" className="i" />
        </Link>
      </div>
    </section>
  );
}
