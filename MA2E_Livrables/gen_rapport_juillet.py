"""Génère le rapport d'activité juillet 2026 à partir de celui de juin.

Copie le fichier juin vers un fichier juillet, puis remplace UNIQUEMENT la
section MA2E (paragraphes 80 à 86 dans le doc source) par le contenu du mois
de juillet. Les sections SNVC et ES-CRC SODECI restent inchangées.
"""
from pathlib import Path
import shutil
from docx import Document

SRC = Path(r"C:\Users\LENOVO\Downloads\RAPPORT D'ACTIVITE GS2E EBAH AFFO ADELE FLORA JUIN 2026.docx")
DST = Path(r"C:\Users\LENOVO\Downloads\RAPPORT D'ACTIVITE GS2E EBAH AFFO ADELE FLORA JUILLET 2026.docx")


# En-tête MA2E (paragraphe 80 dans le doc source)
MA2E_TITLE = (
    "MA2E — Plateforme digitale d'identification et d'enrôlement des sociétaires "
    "de la mutuelle — Sprint 2 : sécurisation, refactorisation UI et activation "
    "des parcours secondaires."
)

# 5 items MA2E pour Juillet 2026 (déploiement retiré, textes raccourcis)
MA2E_ITEMS_JULY = [
    "Sécurisation complète : migration de l'authentification vers cookies "
    "httpOnly, mise en place du CSRF double-submit et du refresh token à "
    "rotation Redis, rate-limit multi-buckets, MFA TOTP, scrubber PII et "
    "headers HSTS/CSP.",

    "Refactorisation du frontend Next.js : découpage de vingt-et-une pages "
    "en modules sous deux cent cinquante lignes, création d'une bibliothèque "
    "UI partagée, unification des sidebars et migration typographique.",

    "Finalisation des trois parcours conversationnels secondaires — "
    "Consultation de dossier, Mise à jour d'informations, Chat libre (RAG) — "
    "avec trois nouvelles actions backend et un mécanisme de bascule "
    "inter-parcours dans le moteur de workflow.",

    "Amélioration du moteur de workflow et des contrôles anti-fraude : "
    "ordre déterministe des parcours actifs, résolution des branches "
    "conditionnelles, correction du contrôle de cohérence OCR recto/verso.",

    "Préparation du CVATL Q2 et des livrables de passation : dossier "
    "d'architecture, manuel utilisateur v2, portefeuille technique consolidé.",
]


def _replace_paragraph_text(paragraph, new_text: str):
    """Remplace le texte d'un paragraphe en préservant le style du premier run."""
    if not paragraph.runs:
        # Paragraphe vide (rare) — insère un run neuf
        paragraph.add_run(new_text)
        return
    # Vide tous les runs sauf le premier (pour préserver son formatage)
    first_run = paragraph.runs[0]
    for r in paragraph.runs[1:]:
        r.text = ""
    first_run.text = new_text


def _replace_juin_partout(doc):
    """Remplace toutes les occurrences de Juin/juin/JUIN par la variante juillet
    correspondante — paragraphes body + headers + footers + cellules de tableaux."""
    def _swap(text: str) -> str:
        return (text.replace("JUIN", "JUILLET")
                    .replace("Juin", "Juillet")
                    .replace("juin", "juillet"))

    def _walk_paragraphs(paragraphs):
        for p in paragraphs:
            if "juin" in p.text.lower():
                _replace_paragraph_text(p, _swap(p.text))

    _walk_paragraphs(doc.paragraphs)
    for section in doc.sections:
        _walk_paragraphs(section.header.paragraphs)
        _walk_paragraphs(section.footer.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                _walk_paragraphs(cell.paragraphs)


def _reset_synthese_tache_table(doc):
    """Table 0 (synthèse des tâches) : renomme la ligne JUIN en JUILLET et
    remet tous les compteurs à 0 (jusqu'à ce qu'on ait des chiffres réels)."""
    if not doc.tables:
        return
    table = doc.tables[0]
    if len(table.rows) < 3:
        return
    for row_idx in (1, 2):  # r1 = JUIN(→JUILLET), r2 = TOTAL
        row = table.rows[row_idx]
        for col_idx in range(1, len(row.cells)):
            cell = row.cells[col_idx]
            for p in cell.paragraphs:
                # Détecte si la valeur est un pourcentage
                is_pct = "%" in p.text
                _replace_paragraph_text(p, "0%" if is_pct else "0")


def build():
    shutil.copy(SRC, DST)
    doc = Document(DST)

    # ── Remplace TOUS les Juin/JUIN par Juillet/JUILLET (partout) ──────
    _replace_juin_partout(doc)

    # ── Réinitialise le tableau Synthèse des tâches (0 partout) ────────
    _reset_synthese_tache_table(doc)

    # ── Réécriture uniquement de la section MA2E ───────────────────────
    # Repère le titre MA2E (paragraphe qui commence par "MA2E")
    paragraphs = doc.paragraphs
    ma2e_start = None
    for i, p in enumerate(paragraphs):
        stripped = p.text.strip()
        if stripped.startswith("MA2E") and "Plateforme" in stripped:
            ma2e_start = i
            break
    if ma2e_start is None:
        raise RuntimeError("Section MA2E introuvable")

    # Repère la fin (paragraphe qui commence par "ES-CRC" ou "SODECI")
    ma2e_end = None
    for i in range(ma2e_start + 1, len(paragraphs)):
        stripped = paragraphs[i].text.strip()
        if stripped.startswith("ES-CRC") or stripped.startswith("SNVC"):
            ma2e_end = i - 1
            break
    if ma2e_end is None:
        raise RuntimeError("Fin de section MA2E introuvable")

    ma2e_items_indices = list(range(ma2e_start + 1, ma2e_end + 1))
    if len(ma2e_items_indices) != len(MA2E_ITEMS_JULY):
        print(f"[info] {len(ma2e_items_indices)} paragraphes existants -> "
              f"{len(MA2E_ITEMS_JULY)} items juillet (surnumeraires vides)")

    # Remplace le titre MA2E (en conservant "\nActions :" si présent)
    title_para = paragraphs[ma2e_start]
    # Le paragraphe titre a souvent 2 runs : titre + "\nActions :"
    if len(title_para.runs) >= 2 and "Actions" in title_para.runs[1].text:
        title_para.runs[0].text = MA2E_TITLE
        # runs[1] conserve son "\nActions :"
    else:
        _replace_paragraph_text(title_para, MA2E_TITLE + "\nActions :")

    # Remplace les items MA2E un à un
    to_remove = []
    for idx, para_idx in enumerate(ma2e_items_indices):
        if idx < len(MA2E_ITEMS_JULY):
            _replace_paragraph_text(paragraphs[para_idx], MA2E_ITEMS_JULY[idx])
        else:
            # Paragraphes en trop (moins d'items juillet que juin) → à supprimer
            to_remove.append(paragraphs[para_idx])

    for p in to_remove:
        el = p._element
        el.getparent().remove(el)

    doc.save(DST)
    print(f"[ok] {DST}")


if __name__ == "__main__":
    build()
