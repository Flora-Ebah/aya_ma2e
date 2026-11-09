"use client";
import { Icon } from "@/components/Icon";
import {
  fmtDate, prettifyPieceType, prettifySituation,
} from "./_constants";
import { KVRow, KVTable, SectionBlock } from "./_SectionBlock";

/* ============================================================ */
/*  Vue d'ensemble (notes de revue + synthèse)                    */
/* ============================================================ */
export function VueEnsemble({ dossier, sociétaireName }: { dossier: any; sociétaireName: string }) {
  return (
    <>
      {dossier.priority_review && (
        <InlineNote
          tone="warning" icon="flag-01"
          label="Revue prioritaire — arbitrage requis"
          text={dossier.priority_reason || "Ce dossier a été signalé pour examen manuel."}
        />
      )}
      {dossier.rejection_motive && (
        <InlineNote tone="error" icon="cancel-circle" label="Motif de rejet" text={dossier.rejection_motive} />
      )}
      {dossier.additional_request && (
        <InlineNote tone="warning" icon="alert-circle" label="Complément demandé" text={dossier.additional_request} />
      )}

      <SectionBlock id="vue-ensemble" title="Vue d'ensemble" subtitle="Synthèse du dossier">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <KVTable>
            <KVRow label="N° de dossier" value={dossier.dossier_number} mono />
            <KVRow label="N° sociétaire" value={dossier.numero_societaire} mono />
            <KVRow label="Sociétaire" value={sociétaireName} />
          </KVTable>
          <KVTable>
            <KVRow label="Créé le" value={dossier.created_at ? fmtDate(dossier.created_at) : null} />
            <KVRow label="Soumis le" value={dossier.submitted_at ? fmtDate(dossier.submitted_at) : null} />
            <KVRow label="Validé le" value={dossier.validated_at ? fmtDate(dossier.validated_at) : null} />
          </KVTable>
        </div>
      </SectionBlock>
    </>
  );
}

function InlineNote({ tone, icon, label, text }: {
  tone: "error" | "warning"; icon: string; label: string; text: string;
}) {
  return (
    <div className={`sa-alert sa-alert--${tone}`} role="note">
      <Icon name={icon} className="i" />
      <div className="sa-alert__body">
        <span className="sa-alert__title">{label}</span>
        <p className="sa-alert__text" style={{ margin: 0 }}>{text}</p>
      </div>
    </div>
  );
}

/* ============================================================ */
/*  Sections KVTable business (7 blocs)                          */
/* ============================================================ */

export function SocietaireSection({ dossier, sociétaireName }: { dossier: any; sociétaireName: string }) {
  return (
    <SectionBlock id="societaire" title="Sociétaire">
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
    >
      <KVTable>
        <KVRow label="Matricule" value={dossier.matricule} mono />
        <KVRow label="Société employeur" value={dossier.employeur_code} />
        <KVRow label="Direction / Service" value={dossier.donnees_pro?.extra?.direction_service} />
        <KVRow label="Exploitation / site" value={dossier.donnees_pro?.extra?.exploitation_site} />
        <KVRow label="Boîte postale" value={dossier.donnees_pro?.extra?.boite_postale_choisie} />
        <KVRow label="Profession" value={dossier.donnees_pro?.fonction} />
        <KVRow label="Catégorie" value={dossier.donnees_pro?.extra?.categorie} />
        <KVRow label="Date d'embauche" value={dossier.donnees_pro?.extra?.date_embauche} />
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
    >
      <KVTable>
        <KVRow label="Téléphone principal" value={dossier.end_user?.phone} mono />
        <KVRow label="Téléphone cellulaire" value={dossier.end_user?.extra?.telephone_cellulaire} mono />
        <KVRow label="Téléphone domicile" value={dossier.end_user?.extra?.telephone_domicile} mono />
        <KVRow label="Téléphone bureau" value={dossier.end_user?.extra?.telephone_bureau} mono />
        <KVRow label="Téléphone secondaire" value={dossier.end_user?.extra?.telephone2} mono />
        <KVRow label="Email" value={dossier.end_user?.extra?.email} mono />
        <KVRow label="Domicile" value={dossier.donnees_pro?.extra?.domicile} />
      </KVTable>
    </SectionBlock>
  );
}

export function FamilleSection({ dossier }: { dossier: any }) {
  return (
    <SectionBlock
      id="famille" title="Famille & personne à prévenir"
      subtitle="Formulaire d'inscription · champs 17-21"
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
    >
      <KVTable>
        <KVRow label="IBAN" value={null} />
        <KVRow label="Banque" value={null} />
        <KVRow label="Titulaire" value={null} />
      </KVTable>
      <p className="sa-help" style={{ margin: 0 }}>
        Collecte RIB pour versement des prestations — prévu Sprint 1, accès via rôle DPO uniquement.
      </p>
    </SectionBlock>
  );
}
