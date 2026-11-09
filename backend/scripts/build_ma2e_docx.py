"""Génère deux documents Word (format "humain") pour tester l'extraction LLM.

Chaque .docx contient :
- un titre (parcours name)
- une courte intro
- la liste numérotée des questions / champs à collecter

C'est le format minimaliste attendu par /api/parcours/extract : le LLM
reconstruit derrière le JSON structuré complet (types, validations, chaînage,
welcome, consent ARTCI, OTP, récap, completion).

Les champs reproduisent les PDFs source :
- FICHE D'INSCRIPTION SOCIETAIRE
- DEMANDE DE MISE A JOUR DE COMPTE
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt


INSCRIPTION_TITLE = "Inscription sociétaire"
INSCRIPTION_INTRO = (
    "Ce parcours permet à un nouveau sociétaire GS2E / MA2E de créer son dossier "
    "d'identification en ligne, dans le respect de la loi ivoirienne sur la protection "
    "des données personnelles (ARTCI)."
)
INSCRIPTION_QUESTIONS = [
    "Civilité (M, Mme, Mlle)",
    "Nom de famille",
    "Prénoms",
    "Date de naissance",
    "Lieu de naissance",
    "Situation matrimoniale (Célibataire, Marié(e), Divorcé(e), Veuf(ve))",
    "Type de pièce d'identité (CNI, Passeport, Permis de conduire)",
    "Numéro de la pièce d'identité",
    "Photo recto de la pièce d'identité",
    "Photo verso de la pièce d'identité",
    "Adresse de domicile (quartier, commune, ville)",
    "Boîte postale",
    "Numéro de téléphone (format +225...)",
    "Adresse email (une vérification OTP sera envoyée)",
    "Profession",
    "Matricule GS2E",
    "Catégorie professionnelle",
    "Employeur (nom de la société)",
    "Nom et prénoms du conjoint (si marié)",
    "Nom de jeune fille de la mère",
    "Personne à prévenir en cas d'urgence (nom, lien, téléphone)",
    "Ayant droit déclaré (nom, lien de parenté)",
    "Signature manuscrite (photo)",
    "Consentement ARTCI pour le traitement des données personnelles",
    "Récapitulatif et confirmation finale",
]

MAJ_TITLE = "Mise à jour de compte"
MAJ_INTRO = (
    "Ce parcours permet à un sociétaire existant GS2E / MA2E de mettre à jour "
    "les informations de son dossier d'identification. Les données déjà en base sont "
    "préchargées grâce au matricule."
)
MAJ_QUESTIONS = [
    "Matricule GS2E (le dossier existant est automatiquement retrouvé)",
    "Nom complet (confirmation)",
    "Date de naissance",
    "Lieu de naissance",
    "Numéro CNI",
    "Période de validité de la CNI (du JJ/MM/AAAA au JJ/MM/AAAA)",
    "Situation matrimoniale",
    "Fonction actuelle",
    "Service d'affectation",
    "Boîte postale",
    "Catégorie professionnelle",
    "Société (ex: GS2E, CIE, SODECI)",
    "Direction",
    "Exploitation / site",
    "Date d'embauche",
    "Nom et prénoms du conjoint",
    "Nom de jeune fille de la mère",
    "Téléphone du domicile",
    "Téléphone du bureau",
    "Téléphone cellulaire (vérification OTP)",
    "Adresse email",
    "Personne à prévenir (nom, lien, téléphone)",
    "Ayants droit (nom, lien de parenté) — plusieurs possibles",
    "Récapitulatif des modifications et confirmation finale",
]


def _build_docx(title: str, intro: str, questions: list[str], out_path: Path) -> None:
    doc = Document()

    # Style par défaut un peu plus lisible
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Titre
    heading = doc.add_heading(title, level=0)
    heading.alignment = 1  # center

    # Intro
    p = doc.add_paragraph(intro)
    p.paragraph_format.space_after = Pt(12)

    doc.add_heading("Questions à poser (dans l'ordre)", level=1)

    for i, q in enumerate(questions, start=1):
        doc.add_paragraph(f"{i}. {q}")

    doc.add_paragraph()
    note = doc.add_paragraph()
    run = note.add_run(
        "Note : le chatbot ajoutera automatiquement un message d'accueil au "
        "début, les validations (regex téléphone, email, dates), un OTP pour "
        "l'email/téléphone, un récapitulatif avant confirmation et un message "
        "de clôture avec la référence du dossier."
    )
    run.italic = True

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    print(f"  OK -> {out_path}")


def main() -> None:
    out_dir = Path.home() / "Downloads"
    print(f"Génération des parcours MA2E dans {out_dir} :")
    _build_docx(
        INSCRIPTION_TITLE,
        INSCRIPTION_INTRO,
        INSCRIPTION_QUESTIONS,
        out_dir / "parcours-inscription-societaire.docx",
    )
    _build_docx(
        MAJ_TITLE,
        MAJ_INTRO,
        MAJ_QUESTIONS,
        out_dir / "parcours-mise-a-jour-compte.docx",
    )
    print("OK.")


if __name__ == "__main__":
    main()
