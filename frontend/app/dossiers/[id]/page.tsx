"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api, GATE_LABELS, getToken, STATUS_LABELS } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import Logo from "@/components/Logo";
import FloatingChatButton from "@/components/FloatingChatButton";
import { useConfirm, useToast } from "@/components/ConfirmProvider";
import {
  IconActivity,
  IconAlertCircle,
  IconArrowLeft,
  IconCheck,
  IconClock,
  IconFileText,
  IconImage,
  IconRefresh,
  IconShield,
  IconUser,
  IconX,
} from "@/components/icons";

const STATUS_PILL: Record<string, string> = {
  en_cours: "bg-ink-100 text-ink-700",
  soumis: "bg-primary-50 text-primary-700",
  en_validation: "bg-accent-50 text-accent-700",
  valide: "bg-primary-100 text-primary-800",
  rejete: "bg-red-50 text-red-700",
  complement_requis: "bg-purple-50 text-purple-700",
};

const STATUS_DOT: Record<string, string> = {
  en_cours: "bg-ink-400",
  soumis: "bg-primary-500",
  en_validation: "bg-accent-500",
  valide: "bg-primary-600",
  rejete: "bg-red-500",
  complement_requis: "bg-purple-500",
};

const FIELD_LABELS: Record<string, string> = {
  numero_piece: "N° de pièce",
  nom: "Nom",
  prenoms: "Prénoms",
  sexe: "Sexe",
  date_naissance: "Date de naissance",
  lieu_naissance: "Lieu de naissance",
  nationalite: "Nationalité",
  date_delivrance: "Date de délivrance",
  date_expiration: "Date d'expiration",
  adresse: "Adresse",
  document_number: "N° document",
  document_type: "Type document",
  issuing_country: "Pays émetteur",
  date_naissance_iso: "Date de naissance",
  date_expiration_iso: "Date d'expiration",
};

const AUDIT_LABELS: Record<string, { label: string; tone: string }> = {
  dossier_created: { label: "Dossier créé", tone: "bg-ink-100 text-ink-700" },
  dossier_submitted: { label: "Dossier soumis", tone: "bg-primary-50 text-primary-700" },
  dossier_validated: { label: "Dossier validé", tone: "bg-primary-100 text-primary-800" },
  dossier_rejected: { label: "Dossier rejeté", tone: "bg-red-50 text-red-700" },
  dossier_complement_requested: { label: "Complément / Mise à jour", tone: "bg-purple-50 text-purple-700" },
  piece_uploaded: { label: "Pièce téléversée", tone: "bg-accent-50 text-accent-700" },
  piece_ocr_completed: { label: "OCR effectué", tone: "bg-primary-50 text-primary-700" },
  piece_viewed: { label: "Pièce consultée", tone: "bg-ink-100 text-ink-600" },
  consent_given: { label: "Consentement signé", tone: "bg-primary-100 text-primary-800" },
  consent_refused: { label: "Consentement refusé", tone: "bg-red-50 text-red-700" },
  consent_revoked: { label: "Consentement révoqué", tone: "bg-red-50 text-red-700" },
};

const TOC = [
  { id: "vue-ensemble", label: "Vue d'ensemble" },
  { id: "societaire", label: "Sociétaire" },
  { id: "identite", label: "Identité officielle" },
  { id: "profession", label: "Données professionnelles" },
  { id: "famille", label: "Famille & ayants droit" },
  { id: "rib", label: "Coordonnées bancaires" },
  { id: "consentements", label: "Consentements ARTCI" },
  { id: "audit", label: "Historique & audit" },
];

function fmtDate(d?: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function fmtDateTime(d?: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
}

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const y = el.getBoundingClientRect().top + window.scrollY - 80;
  window.scrollTo({ top: y, behavior: "smooth" });
}

export default function DossierDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const confirm = useConfirm();
  const toast = useToast();

  const [dossier, setDossier] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectMotive, setRejectMotive] = useState("");
  const [showComplementModal, setShowComplementModal] = useState(false);
  const [complementText, setComplementText] = useState("");
  const [zoomImage, setZoomImage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>("vue-ensemble");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [params.id, router]);

  useEffect(() => {
    if (!dossier) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 }
    );
    TOC.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [dossier]);

  async function load() {
    setLoading(true);
    try {
      setDossier(await api.getDossier(params.id));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onValidate() {
    const ok = await confirm({
      title: "Valider ce dossier ?",
      message: (
        <>
          Le dossier <strong className="font-medium text-ink-900">{dossier.dossier_number}</strong>{" "}
          sera marqué <strong className="text-primary-700 font-medium">validé</strong>. Le sociétaire
          sera notifié.
        </>
      ),
      confirmText: "Valider",
      variant: "success",
      icon: "success",
    });
    if (!ok) return;
    setActionLoading(true);
    try {
      await api.validateDossier(params.id);
      await load();
      toast({ tone: "success", title: "Dossier validé", message: `${dossier.dossier_number} validé.` });
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setActionLoading(false);
    }
  }

  async function onReject() {
    if (!rejectMotive.trim()) return;
    setActionLoading(true);
    try {
      await api.rejectDossier(params.id, rejectMotive);
      setShowRejectModal(false);
      setRejectMotive("");
      await load();
      toast({ tone: "info", title: "Dossier rejeté", message: "Le sociétaire a été notifié." });
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setActionLoading(false);
    }
  }

  async function onComplement() {
    if (!complementText.trim()) return;
    setActionLoading(true);
    try {
      await api.complementDossier(params.id, complementText);
      setShowComplementModal(false);
      setComplementText("");
      await load();
      toast({ tone: "info", title: "Complément demandé", message: "La demande a été envoyée." });
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F6FAF7]">
        <Sidebar />
        <FloatingChatButton />
        <div className="lg:pl-64 p-12 text-center text-ink-400 text-sm">Chargement…</div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen bg-[#F6FAF7]">
        <Sidebar />
        <FloatingChatButton />
        <div className="lg:pl-64 max-w-3xl mx-auto p-8">
          <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 text-red-800 rounded p-4">
            <IconAlertCircle size={20} className="text-red-500 shrink-0 mt-0.5" />
            <span className="text-[13px]">{error}</span>
          </div>
        </div>
      </div>
    );
  }
  if (!dossier) return null;

  const recto = dossier.pieces.find((p: any) => p.face === "recto");
  const verso = dossier.pieces.find((p: any) => p.face === "verso");
  const canAct = dossier.status === "soumis" || dossier.status === "en_validation";
  const sociétaireName = dossier.end_user.name || "—";
  const consents = dossier.consentements || [];

  return (
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar />
      <FloatingChatButton />

      <main className="lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-5">
            <Link
              href="/dossiers"
              className="inline-flex items-center gap-1.5 text-[13px] text-ink-700 hover:text-primary-700 font-medium transition"
            >
              <IconArrowLeft size={14} />
              Détails du dossier
            </Link>
            {canAct && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowComplementModal(true)}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1.5 text-[12.5px] bg-white hover:bg-ink-50 text-ink-700 border border-ink-200 rounded-sm px-3 py-2 transition disabled:opacity-50"
                >
                  <IconRefresh size={13} />
                  Demander complément
                </button>
                <button
                  onClick={() => setShowRejectModal(true)}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1.5 text-[12.5px] bg-white hover:bg-red-50 text-red-700 border border-red-200 rounded-sm px-3 py-2 transition disabled:opacity-50"
                >
                  <IconX size={13} />
                  Rejeter
                </button>
                <button
                  onClick={onValidate}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1.5 text-[12.5px] bg-primary-600 hover:bg-primary-700 text-white rounded-sm px-3 py-2 transition shadow-sm disabled:opacity-50 font-medium"
                >
                  <IconCheck size={13} />
                  Valider le dossier
                </button>
              </div>
            )}
          </div>

          <div className="flex gap-6">
            <aside className="hidden lg:block w-52 shrink-0">
              <div className="sticky top-6 space-y-1">
                <div className="text-[10px] uppercase tracking-[0.14em] text-ink-400 font-semibold mb-2 px-3">
                  Sommaire
                </div>
                {TOC.map((item, idx) => {
                  const active = activeSection === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => scrollToSection(item.id)}
                      className={`w-full text-left flex items-center gap-2.5 px-3 py-1.5 rounded-sm text-[12.5px] transition ${
                        active
                          ? "bg-primary-50 text-primary-700 font-medium"
                          : "text-ink-600 hover:bg-white hover:text-ink-900 font-normal"
                      }`}
                    >
                      <span
                        className={`text-[10.5px] font-mono ${
                          active ? "text-primary-500" : "text-ink-400"
                        }`}
                      >
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}

                <div className="mt-4 pt-4 border-t border-ink-100 px-3">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-ink-400 font-semibold mb-1.5">
                    Conformité
                  </div>
                  <div className="text-[11px] text-ink-500 font-light leading-relaxed">
                    {consents.filter((c: any) => c.decision === "accepte").length} / 3 consentements signés
                  </div>
                </div>
              </div>
            </aside>

            <div className="flex-1 min-w-0 bg-white border border-ink-100 rounded-sm p-8">
              {/* ====== VUE D'ENSEMBLE ====== */}
              <section id="vue-ensemble" className="scroll-mt-24">
                <div className="flex items-start justify-between mb-8">
                  <div>
                    <div className="grid grid-cols-2 gap-x-12 gap-y-3 mb-6">
                      <div>
                        <div className="text-[10.5px] uppercase tracking-[0.14em] text-ink-400 font-medium mb-1">
                          Numéro de dossier
                        </div>
                        <div className="text-[13.5px] font-semibold text-ink-900 font-mono">
                          {dossier.dossier_number}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10.5px] uppercase tracking-[0.14em] text-ink-400 font-medium mb-1">
                          Date de soumission
                        </div>
                        <div className="text-[13.5px] font-semibold text-ink-900">
                          {fmtDate(dossier.submitted_at || dossier.created_at)}
                        </div>
                      </div>
                    </div>

                    <h1 className="text-[32px] font-bold text-ink-900 tracking-tight leading-none mb-2">
                      {sociétaireName}
                    </h1>
                    <div className="text-[12.5px] text-ink-500 font-light leading-relaxed">
                      Mutuelle des Agents de l'Eau et de l'Électricité — MA2E
                      <br />
                      Sociétaire {dossier.employeur_code ? `· ${dossier.employeur_code}` : ""}
                      {dossier.end_user.phone ? ` · ${dossier.end_user.phone}` : ""}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-3">
                    <Logo size={56} />
                    <span className={`badge ${STATUS_PILL[dossier.status]} !text-[11px] !py-1 !px-2.5`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[dossier.status]}`} />
                      {STATUS_LABELS[dossier.status]}
                    </span>
                  </div>
                </div>

                <div className="border-t border-ink-200 -mx-8" />

                {dossier.rejection_motive && (
                  <div className="mt-6 bg-red-50/60 border-l-2 border-red-500 px-4 py-3 rounded-sm">
                    <div className="text-[10px] uppercase tracking-[0.14em] font-semibold mb-0.5 text-red-700">
                      Motif de rejet
                    </div>
                    <div className="text-[13px] text-red-900 font-light leading-relaxed">
                      {dossier.rejection_motive}
                    </div>
                  </div>
                )}
                {dossier.additional_request && (
                  <div className="mt-6 bg-purple-50/60 border-l-2 border-purple-500 px-4 py-3 rounded-sm">
                    <div className="text-[10px] uppercase tracking-[0.14em] font-semibold mb-0.5 text-purple-700">
                      Complément demandé
                    </div>
                    <div className="text-[13px] text-purple-900 font-light leading-relaxed">
                      {dossier.additional_request}
                    </div>
                  </div>
                )}
              </section>

              {/* ====== SOCIÉTAIRE ====== */}
              <SectionBlock id="societaire" title="Sociétaire" icon={<IconUser size={14} />}>
                <KVTable>
                  <KVRow label="Nom complet" value={sociétaireName} />
                  <KVRow label="Téléphone WhatsApp" value={dossier.end_user.phone} mono />
                  <KVRow label="Identifiant interne" value={dossier.end_user.id} mono small />
                </KVTable>
              </SectionBlock>

              {/* ====== IDENTITÉ OFFICIELLE ====== */}
              <SectionBlock
                id="identite"
                title="Identité officielle"
                subtitle="Pièces d'identité · OCR Mindee · MRZ ICAO 9303"
                icon={<IconFileText size={14} />}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
                  <PhotoCard piece={recto} face="recto" onZoom={setZoomImage} />
                  <PhotoCard piece={verso} face="verso" onZoom={setZoomImage} />
                </div>

                <DataTable
                  title="Identité (Recto)"
                  data={recto?.ocr_data || {}}
                  fieldLabels={FIELD_LABELS}
                  total={
                    recto?.ocr_confidence != null
                      ? `Confiance OCR ${Math.round(recto.ocr_confidence * 100)}%`
                      : null
                  }
                />

                {verso?.mrz_data && Object.keys(verso.mrz_data.parsed || {}).length > 0 && (
                  <div className="mt-5">
                    <DataTable
                      title="Zone MRZ (Verso · ICAO 9303)"
                      data={verso.mrz_data.parsed}
                      fieldLabels={FIELD_LABELS}
                      mrzLines={
                        [verso.mrz_data.line1, verso.mrz_data.line2].filter(Boolean) as string[]
                      }
                      total={
                        verso?.ocr_confidence != null
                          ? `Confiance OCR ${Math.round(verso.ocr_confidence * 100)}%`
                          : null
                      }
                    />
                  </div>
                )}
              </SectionBlock>

              {/* ====== DONNÉES PROFESSIONNELLES ====== */}
              <SectionBlock
                id="profession"
                title="Données professionnelles"
                subtitle="PRD §6.4 · Périmètre MA2E"
                icon={<IconFileText size={14} />}
              >
                <KVTable>
                  <KVRow label="Matricule" value={dossier.matricule} mono />
                  <KVRow label="Employeur" value={dossier.employeur_code} />
                  <KVRow label="Fonction" value={dossier.donnees_pro?.fonction} />
                  <KVRow
                    label="Ancienneté"
                    value={
                      dossier.donnees_pro?.anciennete_annees != null
                        ? `${dossier.donnees_pro.anciennete_annees} ans`
                        : null
                    }
                  />
                  <KVRow
                    label="Situation familiale"
                    value={dossier.donnees_pro?.situation_familiale}
                  />
                </KVTable>
              </SectionBlock>

              {/* ====== FAMILLE & AYANTS DROIT ====== */}
              <SectionBlock
                id="famille"
                title="Famille & ayants droit"
                subtitle="PRD §6.4 · entité `ayant_droit`"
                icon={<IconUser size={14} />}
              >
                <KVTable>
                  <KVRow
                    label="Situation matrimoniale"
                    value={dossier.donnees_pro?.situation_familiale}
                  />
                  <KVRow
                    label="Nombre d'ayants droit déclarés"
                    value={String(dossier.donnees_pro?.nombre_ayants_droit ?? 0)}
                  />
                </KVTable>
                <div className="mt-3 text-[12px] text-ink-400 font-light italic">
                  Détail conjoint + enfants (état civil, dates de naissance) — prévu Sprint 1, épic
                  PRO §6.4.
                </div>
              </SectionBlock>

              {/* ====== RIB ====== */}
              <SectionBlock
                id="rib"
                title="Coordonnées bancaires (RIB)"
                subtitle="PRD §9 · accès restreint, chiffrement champ par champ"
                icon={<IconFileText size={14} />}
              >
                <KVTable>
                  <KVRow label="IBAN" value={<span className="text-ink-300">Non renseigné</span>} />
                  <KVRow label="Banque" value={<span className="text-ink-300">—</span>} />
                  <KVRow label="Titulaire" value={<span className="text-ink-300">—</span>} />
                </KVTable>
                <div className="mt-3 text-[12px] text-ink-400 font-light italic">
                  Collecte RIB pour versement des prestations — prévu Sprint 1, accès via rôle DPO
                  uniquement.
                </div>
              </SectionBlock>

              {/* ====== CONSENTEMENTS ARTCI ====== */}
              <SectionBlock
                id="consentements"
                title="Consentements ARTCI"
                subtitle="Loi 2013-450 · signés HMAC-SHA256"
                icon={<IconShield size={14} />}
              >
                <div className="border-t border-ink-200">
                  {consents.length === 0 && (
                    <div className="text-[12.5px] text-ink-400 font-light italic py-3 text-center">
                      Aucun consentement
                    </div>
                  )}
                  {consents.map((c: any) => (
                    <div
                      key={c.id}
                      className="flex items-center gap-3 py-2.5 border-b border-ink-100 text-[13px]"
                    >
                      <span
                        className={`w-5 h-5 rounded-sm flex items-center justify-center shrink-0 ${
                          c.decision === "accepte"
                            ? "bg-primary-100 text-primary-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {c.decision === "accepte" ? <IconCheck size={11} /> : <IconX size={11} />}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-ink-900 font-medium">
                          {GATE_LABELS[c.gate] || c.gate}
                        </div>
                        <div className="text-[10.5px] text-ink-500 font-light mt-0.5 font-mono truncate">
                          v{c.texte_version} · sig: {c.signature}
                        </div>
                      </div>
                      <span className="text-[12px] text-ink-500 font-light shrink-0">
                        {fmtDateTime(c.created_at)}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between py-3 border-t-2 border-ink-200 mt-1">
                    <div className="text-[12.5px] font-semibold text-ink-900 uppercase tracking-wider">
                      Statut conformité
                    </div>
                    <div className="text-[13px] font-semibold text-primary-700">
                      {consents.filter((c: any) => c.decision === "accepte").length} / 3 signés
                    </div>
                  </div>
                </div>
              </SectionBlock>

              {/* ====== HISTORIQUE / AUDIT ====== */}
              <SectionBlock
                id="audit"
                title="Historique & journal d'audit"
                subtitle="PRD §10.3 · append-only avec hash chaîné SHA-256"
                icon={<IconActivity size={14} />}
              >
                <div className="border-t border-ink-200">
                  {(!dossier.audit_logs || dossier.audit_logs.length === 0) && (
                    <div className="text-[12.5px] text-ink-400 font-light italic py-3 text-center">
                      Aucune entrée d'audit pour ce dossier.
                    </div>
                  )}
                  {(dossier.audit_logs || []).map((log: any) => {
                    const meta = AUDIT_LABELS[log.action] || {
                      label: log.action,
                      tone: "bg-ink-100 text-ink-600",
                    };
                    const actor =
                      log.actor_type === "end_user"
                        ? "Sociétaire"
                        : log.actor_type === "user"
                          ? "Gestionnaire"
                          : "Système";
                    return (
                      <div
                        key={log.id}
                        className="flex items-start gap-3 py-2.5 border-b border-ink-100 last:border-0 text-[13px]"
                      >
                        <span
                          className={`w-5 h-5 rounded-sm flex items-center justify-center shrink-0 mt-0.5 ${meta.tone}`}
                        >
                          <IconActivity size={11} />
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-ink-900 font-medium">{meta.label}</div>
                          <div className="text-[11px] text-ink-500 font-light mt-0.5">
                            {actor}
                            {log.details?.field ? ` · champ ${log.details.field}` : ""}
                            {log.details?.motive ? ` · motif renseigné` : ""}
                          </div>
                        </div>
                        <span className="text-[11.5px] text-ink-500 font-light shrink-0 mt-0.5">
                          {fmtDateTime(log.created_at)}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-5 bg-primary-50/40 border border-primary-100 rounded-sm p-4 flex items-start gap-3">
                  <div className="w-9 h-9 rounded-sm bg-primary-600 text-white flex items-center justify-center shrink-0">
                    <IconShield size={16} />
                  </div>
                  <div className="text-[12px] text-ink-700 leading-relaxed font-light">
                    <strong className="text-ink-900 font-medium">Conformité ARTCI</strong> ·
                    Consentements et événements signés{" "}
                    <span className="font-mono text-[11.5px] bg-white px-1.5 py-0.5 rounded-sm border border-ink-200">
                      HMAC-SHA256
                    </span>
                    , horodatés UTC, inscrits dans le journal d'audit append-only avec hash chaîné
                    SHA-256.
                  </div>
                </div>
              </SectionBlock>
            </div>
          </div>
        </div>
      </main>

      {zoomImage && (
        <div
          className="fixed inset-0 bg-ink-900/85 backdrop-blur z-[55] flex items-center justify-center p-8 cursor-zoom-out animate-fade-in"
          onClick={() => setZoomImage(null)}
        >
          <img
            src={zoomImage}
            alt="Pièce d'identité"
            className="max-w-full max-h-full rounded shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {showRejectModal && (
        <Modal onClose={() => setShowRejectModal(false)} title="Rejeter le dossier" tone="red">
          <p className="text-[12.5px] text-ink-600 mb-3 font-light leading-relaxed">
            Le sociétaire sera notifié du rejet et du motif fourni ci-dessous.
          </p>
          <textarea
            value={rejectMotive}
            onChange={(e) => setRejectMotive(e.target.value)}
            rows={4}
            placeholder="Précisez le motif du rejet…"
            className="input-base"
            autoFocus
          />
          <div className="flex justify-end gap-2 mt-4">
            <button onClick={() => setShowRejectModal(false)} className="btn-secondary">
              Annuler
            </button>
            <button
              onClick={onReject}
              disabled={actionLoading || !rejectMotive.trim()}
              className="btn-danger"
            >
              Rejeter
            </button>
          </div>
        </Modal>
      )}

      {showComplementModal && (
        <Modal
          onClose={() => setShowComplementModal(false)}
          title="Demander un complément"
          tone="default"
        >
          <p className="text-[12.5px] text-ink-600 mb-3 font-light leading-relaxed">
            Le sociétaire recevra la demande sur son canal d'origine.
          </p>
          <textarea
            value={complementText}
            onChange={(e) => setComplementText(e.target.value)}
            rows={4}
            placeholder="Précisez les éléments manquants…"
            className="input-base"
            autoFocus
          />
          <div className="flex justify-end gap-2 mt-4">
            <button onClick={() => setShowComplementModal(false)} className="btn-secondary">
              Annuler
            </button>
            <button
              onClick={onComplement}
              disabled={actionLoading || !complementText.trim()}
              className="btn-primary"
            >
              Envoyer
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function SectionBlock({
  id,
  title,
  subtitle,
  icon,
  children,
}: {
  id: string;
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 pt-8 mt-8 border-t border-ink-100 first:border-0 first:pt-0 first:mt-0">
      <div className="mb-5">
        <div className="flex items-center gap-2.5">
          {icon && (
            <span className="w-7 h-7 rounded-full bg-primary-500/10 text-primary-600 ring-1 ring-primary-500/15 flex items-center justify-center backdrop-blur-sm">
              {icon}
            </span>
          )}
          <span className="text-[12px] font-semibold text-ink-900 uppercase tracking-[0.14em]">
            {title}
          </span>
        </div>
        {subtitle && (
          <div className="text-[11px] text-ink-400 font-light mt-1.5 ml-9">{subtitle}</div>
        )}
      </div>
      {children}
    </section>
  );
}

function KVTable({ children }: { children: React.ReactNode }) {
  return <div className="border-t border-ink-200">{children}</div>;
}

function KVRow({
  label,
  value,
  mono = false,
  small = false,
}: {
  label: string;
  value: any;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 border-b border-ink-100 last:border-0 text-[13px]">
      <span className="text-ink-500 font-light">{label}</span>
      <span
        className={`text-ink-900 font-medium text-right ${mono ? `font-mono ${small ? "text-[11px]" : "text-[12.5px]"}` : ""}`}
      >
        {value ?? <span className="text-ink-300 font-normal">—</span>}
      </span>
    </div>
  );
}

function PhotoCard({
  piece,
  face,
  onZoom,
}: {
  piece: any;
  face: "recto" | "verso";
  onZoom: (url: string) => void;
}) {
  if (!piece) {
    return (
      <div className="border border-dashed border-ink-200 rounded-sm p-10 text-center">
        <IconImage size={26} className="text-ink-300 mx-auto mb-2" />
        <div className="text-[12.5px] text-ink-400 font-light uppercase tracking-wider">
          {face}
        </div>
      </div>
    );
  }
  const imageUrl = piece.storage_key?.startsWith("http") ? piece.storage_key : null;
  const conf = piece.ocr_confidence != null ? Math.round(piece.ocr_confidence * 100) : null;

  return (
    <div className="border border-ink-100 rounded-sm overflow-hidden">
      {imageUrl ? (
        <button
          onClick={() => onZoom(imageUrl)}
          className="block w-full bg-ink-900 cursor-zoom-in"
        >
          <img src={imageUrl} alt={`Pièce ${face}`} className="w-full h-44 object-cover" />
        </button>
      ) : (
        <div className="bg-ink-100 h-44 flex items-center justify-center text-ink-400">
          <IconImage size={26} />
        </div>
      )}
      <div className="flex items-center justify-between px-3 py-2 bg-ink-50">
        <span className="text-[10.5px] uppercase tracking-[0.14em] text-ink-600 font-medium">
          {face}
        </span>
        {conf != null && (
          <span className="text-[11px] font-semibold text-primary-700">{conf}% OCR</span>
        )}
      </div>
    </div>
  );
}

function DataTable({
  title,
  data,
  fieldLabels,
  total,
  mrzLines,
}: {
  title: string;
  data: Record<string, any>;
  fieldLabels: Record<string, string>;
  total?: string | null;
  mrzLines?: string[];
}) {
  const entries = Object.entries(data || {}).filter(([, v]) => v != null && v !== "");
  return (
    <div>
      <div className="text-[12.5px] font-medium text-ink-700 mb-2">{title}</div>
      {mrzLines && mrzLines.length > 0 && (
        <div className="bg-ink-900 text-primary-300 font-mono text-[10.5px] rounded-sm px-3 py-2.5 mb-3 overflow-x-auto whitespace-pre leading-relaxed">
          {mrzLines.join("\n")}
        </div>
      )}
      {entries.length === 0 ? (
        <div className="text-[12.5px] text-ink-400 font-light italic border-t border-ink-200 py-3 text-center">
          Aucune donnée extraite
        </div>
      ) : (
        <div className="border-t border-ink-200">
          {entries.map(([k, v]) => (
            <div
              key={k}
              className="flex items-center justify-between gap-4 py-2.5 border-b border-ink-100 last:border-0 text-[13px]"
            >
              <span className="text-ink-600 font-light">{fieldLabels[k] || k}</span>
              <span className="text-ink-900 font-medium text-right">{String(v)}</span>
            </div>
          ))}
          {total && (
            <div className="flex items-center justify-between py-3 border-t-2 border-ink-200 mt-1">
              <div className="text-[12px] font-semibold text-ink-900 uppercase tracking-wider">
                Confiance
              </div>
              <div className="text-[12.5px] font-semibold text-primary-700">{total}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Modal({
  children,
  onClose,
  title,
  tone = "default",
}: {
  children: React.ReactNode;
  onClose: () => void;
  title: string;
  tone?: "default" | "red";
}) {
  const iconBg = tone === "red" ? "bg-red-50 text-red-600" : "bg-accent-50 text-accent-600";
  const Icon = tone === "red" ? IconX : IconRefresh;
  return (
    <div
      className="fixed inset-0 bg-ink-900/40 backdrop-blur-sm z-[60] flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-sm p-5 w-full max-w-md shadow-floating animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-9 h-9 rounded-sm flex items-center justify-center ${iconBg}`}>
            <Icon size={18} />
          </div>
          <div className="text-[15px] font-semibold text-ink-900">{title}</div>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
