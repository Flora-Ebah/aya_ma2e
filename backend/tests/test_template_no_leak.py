"""Test de non-régression F-09 — pas de fuite de gabarit interne.

Le rapport pentest v1.0 (F-09) a démontré que la fiche récapitulative
affichait `{ocr_extracted_name}`, `{ocr_document_number}` etc. en clair
quand les variables n'étaient pas dans le contexte (POC : simuler
`confirm_ocr` avec un contexte vide).

La reco pentester : "produire une valeur vide ou un libellé neutre plutôt
que le marqueur brut, et n'exposer jamais les noms de variables internes."

Ce test vérifie que :
  1. `_SafeDict.__missing__` retourne un placeholder discret, jamais le
     nom de la variable en clair.
  2. `_scrub_leaked_tokens` efface tout token `{xxx}` résiduel (défense
     en profondeur si `format_map` échoue).
  3. Des accolades légitimes (JSON, code) ne sont PAS massacrées.

Lancer :
    python -m tests.test_template_no_leak
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conversation.workflow_executor import (  # noqa: E402
    _LEAKED_TOKEN_RE,
    _SafeDict,
    _scrub_leaked_tokens,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)


def main() -> int:
    checks = 0

    # ---- 1. _SafeDict ne fuite jamais le nom de la variable ----
    d = _SafeDict({"nom": "Ouattara"})
    _assert(d["nom"] == "Ouattara", "Variable présente est bien renvoyée")
    _assert(d["ocr_extracted_name"] == "—",
            "Variable manquante → '—', jamais '{ocr_extracted_name}'")
    _assert(d["support_phone"] == "—",
            "Variable système manquante → '—' aussi")
    checks += 3

    # ---- 2. format_map + _SafeDict — le PoC pentester ----
    template = (
        "🛑 *PORTE 2/3*\n"
        "Nom : {ocr_extracted_name}\n"
        "Prénoms : {ocr_extracted_firstname}\n"
        "N° pièce : {ocr_document_number}"
    )
    body = template.format_map(_SafeDict({}))
    _assert("{ocr_extracted_name}" not in body,
            "F-09 PoC pentester : plus de {ocr_extracted_name} en clair")
    _assert("{ocr_extracted_firstname}" not in body, "idem prénoms")
    _assert("{ocr_document_number}" not in body, "idem numéro pièce")
    _assert("—" in body, "Placeholder '—' bien présent en remplacement")
    checks += 4

    # ---- 3. _scrub_leaked_tokens (défense en profondeur) ----
    _assert(_scrub_leaked_tokens("Bonjour {nom}") == "Bonjour —",
            "scrub efface un token isolé")
    _assert(_scrub_leaked_tokens("Nom {a}, Prénom {b}, Tel {c}") == "Nom —, Prénom —, Tel —",
            "scrub efface plusieurs tokens dans une phrase")
    _assert(_scrub_leaked_tokens("Aucun token ici.") == "Aucun token ici.",
            "scrub laisse un texte sans token intact")
    checks += 3

    # ---- 4. Le regex NE massacre PAS les accolades légitimes ----
    # Un exemple JSON ne doit pas être détruit par le scrubber : nos regex
    # ne matche que `{identifier}` avec un vrai identifiant Python.
    json_like = 'Exemple : {"nom": "Ouattara"}'
    _assert(_scrub_leaked_tokens(json_like) == json_like,
            "scrub ne casse pas un JSON avec espaces/guillemets")
    _assert(_scrub_leaked_tokens("{}") == "{}",
            "scrub laisse {} vide intact")
    _assert(_scrub_leaked_tokens("{1nom}") == "{1nom}",
            "scrub ne matche pas les identifiants commençant par un chiffre")
    _assert(_scrub_leaked_tokens("{very-long}") == "{very-long}",
            "scrub ne matche pas les identifiants avec tiret")
    checks += 4

    # ---- 5. Cap de longueur (pas de match sur token géant) ----
    huge = "{" + "a" * 100 + "}"
    _assert(_scrub_leaked_tokens(huge) == huge,
            "scrub cap à 64 chars ne matche pas un pattern anormalement long")
    checks += 1

    # ---- 6. Le regex compile bien ----
    _assert(_LEAKED_TOKEN_RE is not None, "regex chargé")
    _assert(_LEAKED_TOKEN_RE.search("{nom}") is not None, "regex matche {nom}")
    _assert(_LEAKED_TOKEN_RE.search("plain text") is None, "regex ne matche pas plain text")
    checks += 3

    print(f"OK — tous les asserts passent ({checks})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
