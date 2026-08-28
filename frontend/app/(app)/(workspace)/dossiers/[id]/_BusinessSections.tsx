"use client";
import Logo from "@/components/Logo";
import { STATUS_LABELS } from "@/lib/api";
import { IconFileText, IconMessage, IconUser } from "@/components/icons";
import {
  fmtDate, prettifyPieceType, prettifySituation, STATUS_DOT, STATUS_PILL,
} from "./_constants";
import { KVRow, KVTable, SectionBlock } from "./_SectionBlock";

/* ============================================================ */
/*  Vue d'ensemble (header + notes rejet/complément)             */
/* ============================================================ */
export function VueEnsemble({ dossier, sociétaireName }: { dossier: any; sociétaireName: string }) {
  return (
    <section id="vue-ensemble" className="scroll-mt-24">
      <div className="flex items-start justify-between mb-7 gap-4">
        <div className="min-w-0">
          <div className="grid grid-cols-2 gap-x-10 gap-y-2 mb-5">
            <Eyebrow label="Numéro de dossier" value={<span className="font-mono">{dossier.dossier_number}</span>} />
            <Eyebrow label="Date de soumission" value={fmtDate(dossier.submitted_at || dossier.created_at)} />
          </div>
          <h1 className="text-[24px] font-medium text-ink-900 tracking-tight leading-none mb-2">
            {sociétaireName}
          </h1>
          <div className="text-[11.5px] text-ink-500 font-light leading-relaxed">
            Mutuelle des Agents de l&apos;Eau et de l&apos;Électricité — MA2E
            <br />
            Sociétaire {dossier.employeur_code ? `· ${dossier.employeur_code}` : ""}
            {dossier.end_user.phone ? ` · ${dossier.end_user.phone}` : ""}
          </div>
        </div>
        <div className="flex flex-col items-end gap-3 shrink-0">
          <Logo size={48} />
          <span
            className={`inline-flex items-center gap-1.5 text-[9.5px] font-medium uppercase tracking-[0.06em] px-2 py-0.5 rounded ${STATUS_PILL[dossier.status] || ""}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[dossier.status]}`} />
            {STATUS_LABELS[dossier.status]}
          </span>
        </div>
      </div>
      <div className="border-t border-dashed border-ink-300 -mx-8" />
      {dossier.priority_review && (
        <InlineNote
          tone="amber"
          label="Revue prioritaire — arbitrage requis"
          text={dossier.priority_reason || "Ce dossier a été signalé pour examen manuel."}
        />
      )}
      {dossier.rejection_motive && (
        <InlineNote tone="red" label="Motif de rejet" text={dossier.rejection_motive} />
      )}
      {dossier.additional_request && (
        <InlineNote tone="purple" label="Complément demandé" text={dossier.additional_request} />
      )}
    </section>
  );
}

function Eyebrow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-[9.5px] uppercase tracking-[0.14em] text-ink-400 font-medium mb-1">{label}</div>
      <div className="text-[12px] font-medium text-ink-900">{value}</div>
    </div>
  );
}

function InlineNote({ tone, label, text }: { tone: "red" | "purple" | "amber"; label: string; text: string }) {
  const cfg =
    tone === "red"
      ? { bg: "bg-red-50/60 border-red-500", labelColor: "text-red-700", textColor: "text-red-900" }
    : tone === "purple"
      ? { bg: "bg-purple-50/60 border-purple-500", labelColor: "text-purple-700", textColor: "text-purple-900" }
      : { bg: "bg-amber-50/60 border-amber-500", labelColor: "text-amber-700", textColor: "text-amber-900" };
  return (
    <div className={`mt-5 border-l-2 px-4 py-2.5 rounded-sm ${cfg.bg}`}>
      <div className={`text-[9.5px] uppercase tracking-[0.14em] font-medium mb-0.5 ${cfg.labelColor}`}>
        {label}
      </div>
      <div className={`text-[12px] font-light leading-relaxed ${cfg.textColor}`}>{text}</div>
    </div>
  );
}

/* ============================================================ */
/*  Sections KVTable business (7 blocs)                          */
/* ============================================================ */

export function SocietaireSection({ dossier, sociétaireName }: { dossier: any; sociétaireName: string }) {
  return (
    <SectionBlock id="societaire" title="Sociétaire" icon={<IconUser size={13} />}>
      <KVTable>
        <KVRow label="Nom complet" value={sociétaireName} />
        <KVRow label="Téléphone WhatsApp" value={dossier.end_user.phone} mono />
        <KVRow label="Identifiant interne" value={dossier.end_user.id} mono small />
      </KVTable>
    </SectionBlock>
  );
}

export function EtatCivilSection({ dossier }: { dossier: any }) {
  return (
    <SectionBlock
      id="etat-civil" title="État civil"
      subtitle="Formulaire d'inscription · champs 1, 3-7"
      icon={<IconUser size={13} />}
    >
      <KVTable>
        <KVRow label="Civilité" value={dossier.donnees_pro?.extra?.civilite} />
        <KVRow label="Nom" value={dossier.end_user?.name?.split(" ").slice(-1)[0]} />
        <KVRow label="Prénoms" value={dossier.end_user?.name?.split(" ").slice(0, -1).join(" ")} />
        <KVRow label="Date de naissance" value={dossier.donnees_pro?.extra?.date_naissance} />
        <KVRow label="Lieu de naissance" value={dossier.donnees_pro?.extra?.lieu_naissance} />
        <KVRow label="Situation matrimoniale" value={prettifySituation(dossier.donnees_pro?.situation_familiale)} />
        <KVRow label="Nom de jeune fille de la mère" value={dossier.donnees_pro?.extra?.nom_mere} />
      </KVTable>
    </SectionBlock>
  );
}

export function PieceDeclareeSection({ dossier }: { dossier: any }) {
  return (
    <SectionBlock
      id="piece-decl" title="Pièce d'identité déclarée"
      subtitle="Formulaire d'inscription · champs 8-10"
      icon={<IconFileText size={13} />}
    >
      <KVTable>
        <KVRow label="Type de pièce" value={prettifyPieceType(dossier.donnees_pro?.extra?.type_piece)} />
        <KVRow label="N° de pièce déclaré" value={dossier.donnees_pro?.extra?.numero_piece} mono />
      </KVTable>
    </SectionBlock>
  );
}

export function ProfessionSection({ dossier }: { dossier: any }) {
  return (
    <SectionBlock
      id="profession" title="Données professionnelles"
      subtitle="Formulaire d'inscription · champs 2, 11-12, 16, 22"
      icon={<IconFileText size={13} />}
    >
      <KVTable>
        <KVRow label="Matricule" value={dossier.matricule} mono />
        <KVRow label="Société employeur" value={dossier.employeur_code} />
        <KVRow label="Direction / Service / Exploitation" value={dossier.donnees_pro?.extra?.direction_service} />
        <KVRow label="Boîte postale" value={dossier.donnees_pro?.extra?.boite_postale_choisie} />
        <KVRow label="Profession" value={dossier.donnees_pro?.fonction} />
        <KVRow label="Catégorie" value={dossier.donnees_pro?.extra?.categorie} />
        <KVRow
          label="Ancienneté"
          value={dossier.donnees_pro?.anciennete_annees != null ? `${dossier.donnees_pro.anciennete_annees} ans` : null}
        />
      </KVTable>
    </SectionBlock>
  );
}

export function ContactsSection({ dossier }: { dossier: any }) {
  return (
    <SectionBlock
      id="contacts" title="Coordonnées de contact"
      subtitle="Formulaire d'inscription · champs 13-15"
      icon={<IconMessage size={13} />}
    >
      <KVTable>
        <KVRow label="Téléphone principal" value={dossier.end_user?.phone} mono />
        <KVRow label="Téléphone secondaire" value={dossier.end_user?.extra?.telephone2} mono />
        <KVRow label="Email" value={dossier.end_user?.extra?.email} mono />
      </KVTable>
    </SectionBlock>
  );
}

export function FamilleSection({ dossier }: { dossier: any }) {
  return (
    <SectionBlock
      id="famille" title="Famille & personne à prévenir"
      subtitle="Formulaire d'inscription · champs 17-21"
      icon={<IconUser size={13} />}
    >
      <KVTable>
        <KVRow label="Nom du conjoint(e)" value={dossier.donnees_pro?.extra?.nom_conjoint} />
        <KVRow label="Personne à prévenir" value={dossier.donnees_pro?.extra?.personne_a_prevenir} />
        <KVRow label="Contact 1 (à prévenir)" value={dossier.donnees_pro?.extra?.contact_prevenir_1} mono />
        <KVRow label="Contact 2 (à prévenir)" value={dossier.donnees_pro?.extra?.contact_prevenir_2} mono />
        <KVRow label="Ayant(s) droit" value={dossier.donnees_pro?.extra?.ayants_droit} />
      </KVTable>
    </SectionBlock>
  );
}

export function RibSection() {
  return (
    <SectionBlock
      id="rib" title="Coordonnées bancaires (RIB)"
      subtitle="PRD §9 · accès restreint, chiffrement champ par champ"
      icon={<IconFileText size={13} />}
    >
      <KVTable>
        <KVRow label="IBAN" value={<span className="text-ink-300">Non renseigné</span>} />
        <KVRow label="Banque" value={<span className="text-ink-300">—</span>} />
        <KVRow label="Titulaire" value={<span className="text-ink-300">—</span>} />
      </KVTable>
      <div className="mt-3 text-[11px] text-ink-400 font-light italic">
        Collecte RIB pour versement des prestations — prévu Sprint 1, accès via rôle DPO uniquement.
      </div>
    </SectionBlock>
  );
}
