"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { usePermissions } from "@/lib/usePermissions";
import { useConfirm, useToast } from "@/components/ConfirmProvider";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { StatusBadge } from "../_StatusBadge";
import ActionsBar from "./_ActionsBar";
import AuditSection from "./_AuditSection";
import ConsentSection from "./_ConsentSection";
import IdentitySection from "./_IdentitySection";
import TocSidebar from "./_TocSidebar";
import {
  AnonymizeModal, ComplementModal, ImageZoom, RejectModal,
} from "./_ActionModals";
import {
  ContactsSection, EtatCivilSection, FamilleSection,
  PieceDeclareeSection, ProfessionSection, RibSection,
  SocietaireSection, VueEnsemble,
} from "./_BusinessSections";
import { useDossierDetail } from "./_useDossierDetail";

export default function DossierDetailPage() {
  const params = useParams<{ id: string }>();
  const confirm = useConfirm();
  const toast = useToast();
  const { can } = usePermissions();

  const { dossier, loading, error, rejectMotivePresets, activeSection, reload } =
    useDossierDetail(params.id);

  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectMotive, setRejectMotive] = useState("");
  const [showAnonymizeModal, setShowAnonymizeModal] = useState(false);
  const [anonymizeReason, setAnonymizeReason] = useState("");
  const [showComplementModal, setShowComplementModal] = useState(false);
  const [complementText, setComplementText] = useState("");
  const [zoomImage, setZoomImage] = useState<string | null>(null);

  const canValidate = can("validation", "write");
  const canAnonymize = can("conformite", "write");

  async function onValidate() {
    const ok = await confirm({
      title: "Valider ce dossier ?",
      message: (
        <>
          Le dossier <strong className="sa-mono">{dossier.dossier_number}</strong>{" "}
          sera marqué <strong>validé</strong>. Le sociétaire sera notifié.
        </>
      ),
      confirmText: "Valider",
      variant: "success",
      icon: "success",
    });
    if (!ok) return;
    await runAction(
      () => api.validateDossier(params.id),
      { tone: "success", title: "Dossier validé", message: `${dossier.dossier_number} validé.` },
    );
  }

  async function onReject() {
    if (!rejectMotive.trim()) return;
    await runAction(
      () => api.rejectDossier(params.id, rejectMotive),
      { tone: "info", title: "Dossier rejeté", message: "Le sociétaire a été notifié." },
      () => { setShowRejectModal(false); setRejectMotive(""); },
    );
  }

  async function onComplement() {
    if (!complementText.trim()) return;
    await runAction(
      () => api.complementDossier(params.id, complementText),
      { tone: "info", title: "Complément demandé", message: "La demande a été envoyée." },
      () => { setShowComplementModal(false); setComplementText(""); },
    );
  }

  async function onAnonymize() {
    if (anonymizeReason.trim().length < 10) {
      toast({ tone: "error", title: "Motif trop court", message: "Décrivez le motif (10 caractères min)." });
      return;
    }
    setActionLoading(true);
    try {
      const receipt = await api.anonymizeDossier(params.id, anonymizeReason.trim());
      toast({ tone: "success", title: "Anonymisation exécutée", message: receipt.message });
      setShowAnonymizeModal(false);
      setAnonymizeReason("");
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setActionLoading(false);
    }
  }

  async function runAction(
    call: () => Promise<any>,
    successToast: { tone: "success" | "info"; title: string; message: string },
    onSuccess?: () => void,
  ) {
    setActionLoading(true);
    try {
      await call();
      onSuccess?.();
      await reload();
      toast(successToast);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <DetailSkeleton />;
  if (error) {
    return (
      <>
        <BackLink />
        <div className="sa-alert sa-alert--error" role="alert">
          <Icon name="alert-circle" className="i" />
          <div className="sa-alert__body"><p className="sa-alert__text">{error}</p></div>
        </div>
      </>
    );
  }
  if (!dossier) return null;

  const recto = dossier.pieces.find((p: any) => p.face === "recto");
  const verso = dossier.pieces.find((p: any) => p.face === "verso");
  const sociétaireName = dossier.end_user.name || "—";
  const consents = dossier.consentements || [];

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <nav aria-label="Fil d'Ariane">
            <ol className="sa-breadcrumb">
              <li><Link href="/dossiers">Dossiers</Link></li>
              <li><Icon name="arrow-right-01" className="i" /></li>
              <li><span aria-current="page" className="sa-mono">{dossier.dossier_number}</span></li>
            </ol>
          </nav>
          <h1 className="sa-page-title">{sociétaireName}</h1>
          <div className="sa-row" style={{ marginTop: "var(--spacing-2)" }}>
            <span className="sa-ref sa-mono">{dossier.dossier_number}</span>
            <StatusBadge status={dossier.status} />
            {dossier.employeur_code && <span className="sa-badge sa-badge--neutral">{dossier.employeur_code}</span>}
            {dossier.end_user.phone && <span className="sa-text-soft sa-mono">{dossier.end_user.phone}</span>}
          </div>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="sa-row" style={{ gap: 6 }}>
            <Link href="/dossiers" className="sa-btn sa-btn--ghost sa-btn--sm">
              <Icon name="arrow-left-01" className="i" />
              Retour à la liste
            </Link>
            <a
              href={api.fichePdfUrl(dossier.id)}
              target="_blank"
              rel="noopener"
              className="sa-btn sa-btn--outline sa-btn--sm"
            >
              <Icon name="printer" className="i" />
              Imprimer la fiche
            </a>
          </div>
          <ActionsBar
            dossier={dossier}
            canValidate={canValidate}
            canAnonymize={canAnonymize}
            actionLoading={actionLoading}
            onValidate={onValidate}
            onOpenComplement={() => setShowComplementModal(true)}
            onOpenReject={() => setShowRejectModal(true)}
            onOpenAnonymize={() => setShowAnonymizeModal(true)}
          />
        </div>
      </header>

      <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 items-stretch lg:items-start">
        <TocSidebar
          activeSection={activeSection}
          signedConsentsCount={consents.filter((c: any) => c.decision === "accepte").length}
        />

        <div className="flex-1 min-w-0 flex flex-col gap-4">
          <VueEnsemble dossier={dossier} sociétaireName={sociétaireName} />
          <SocietaireSection dossier={dossier} sociétaireName={sociétaireName} />
          <EtatCivilSection dossier={dossier} />
          <IdentitySection
            recto={recto}
            verso={verso}
            signatureUrl={dossier.donnees_pro?.extra?.signature_url || null}
            onZoom={setZoomImage}
          />
          <PieceDeclareeSection dossier={dossier} />
          <ProfessionSection dossier={dossier} />
          <ContactsSection dossier={dossier} />
          <FamilleSection dossier={dossier} />
          <RibSection />
          <ConsentSection consents={consents} />
          <AuditSection logs={dossier.audit_logs || []} />
        </div>
      </div>

      {zoomImage && <ImageZoom url={zoomImage} onClose={() => setZoomImage(null)} />}

      {showRejectModal && (
        <RejectModal
          motive={rejectMotive}
          presets={rejectMotivePresets}
          actionLoading={actionLoading}
          onMotiveChange={setRejectMotive}
          onClose={() => setShowRejectModal(false)}
          onSubmit={onReject}
        />
      )}

      {showAnonymizeModal && (
        <AnonymizeModal
          reason={anonymizeReason}
          actionLoading={actionLoading}
          onReasonChange={setAnonymizeReason}
          onClose={() => setShowAnonymizeModal(false)}
          onSubmit={onAnonymize}
        />
      )}

      {showComplementModal && (
        <ComplementModal
          text={complementText}
          actionLoading={actionLoading}
          onTextChange={setComplementText}
          onClose={() => setShowComplementModal(false)}
          onSubmit={onComplement}
        />
      )}
    </>
  );
}

function BackLink() {
  return (
    <p style={{ margin: "0 0 var(--spacing-4)" }}>
      <Link href="/dossiers" className="sa-btn sa-btn--ghost sa-btn--sm">
        <Icon name="arrow-left-01" className="i" />
        Retour à la liste
      </Link>
    </p>
  );
}

function DetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Chargement du dossier" className="sa-skeleton-stack">
      <div className="sa-skeleton sa-skeleton--title" style={{ width: 280 }} />
      <div className="sa-skeleton sa-skeleton--text" style={{ width: 200 }} />
      <div className="sa-skeleton sa-skeleton--block" style={{ height: 160 }} />
      <div className="sa-skeleton sa-skeleton--block" style={{ height: 160 }} />
    </div>
  );
}
