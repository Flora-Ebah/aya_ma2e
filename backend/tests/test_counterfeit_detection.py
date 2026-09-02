"""Test de non-régression F-03 — détection de pièces d'identité factices.

Le rapport pentest v1.0 (F-03) a montré qu'un document manifestement
fabriqué (marqué SPECIMEN, avec un numéro « IC000000411 ») était accepté
avec un score de confiance de 88 %. La reco pentester exige un contrôle
d'authenticité + confrontation à un référentiel officiel. Cette dernière
partie est un arbitrage produit (Smile ID / ANI / etc. → coût récurrent),
documenté dans docs/DECISION_F03_referentiel.md.

En attendant l'arbitrage, le module `ocr_guardrails.detect_counterfeit_markers`
bloque au moins les documents portant des marqueurs évidents de spécimen
ou de test. Ce test reproduit le PoC exact du pentester.

Lancer :
    python -m tests.test_counterfeit_detection
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ocr_guardrails import (  # noqa: E402
    _is_suspicious_document_number,
    detect_counterfeit_markers,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        sys.stderr.write(f"FAIL: {msg}\n")
        raise AssertionError(msg)


def main() -> int:
    checks = 0

    # ---- 1. PoC pentester EXACT : SPECIMEN + IC000000411 + 2000-01-01 ----
    raw_text = """
        REPUBLIQUE DE COTE D'IVOIRE
        SPECIMEN
        NOM : SPECIMEN
        PRENOMS : SPECIMEN
        NUMERO : IC000000411
        DATE DE NAISSANCE : 2000-01-01
    """
    fields = {
        "nom": "SPECIMEN",
        "prenoms": "SPECIMEN",
        "numero_piece": "IC000000411",
        "date_naissance": "2000-01-01",
    }
    markers = detect_counterfeit_markers(raw_text, fields)
    _assert(len(markers) > 0,
            "PoC pentester : au moins un marqueur doit être détecté")
    _assert(any("specimen" in m.lower() for m in markers),
            f"PoC pentester : 'SPECIMEN' doit être signalé, got {markers}")
    _assert(any("document_number" in m or "IC000000411" in m for m in markers),
            f"PoC pentester : IC000000411 doit être signalé, got {markers}")
    _assert(any("specimen_in_identity_field" in m for m in markers),
            f"PoC pentester : nom/prénoms SPECIMEN doit être signalé, got {markers}")
    checks += 4

    # ---- 2. Document légitime : aucun marqueur ----
    raw_ok = """
        REPUBLIQUE DE COTE D'IVOIRE
        NOM : OUATTARA
        PRENOMS : AHMED
        NUMERO : C00123456
        DATE DE NAISSANCE : 1985-04-12
    """
    fields_ok = {
        "nom": "OUATTARA",
        "prenoms": "AHMED",
        "numero_piece": "C00123456",
        "date_naissance": "1985-04-12",
    }
    markers = detect_counterfeit_markers(raw_ok, fields_ok)
    _assert(markers == [],
            f"Document légitime ne doit produire AUCUN marqueur, got {markers}")
    checks += 1

    # ---- 3. Marqueurs textuels variés ----
    for marker_word in ("SPÉCIMEN", "ECHANTILLON", "SAMPLE", "DEMO",
                        "TEST", "VOID", "FAKE", "FACTICE", "FICTIF",
                        "DUMMY", "PROTOTYPE", "NOT VALID", "NON VALIDE"):
        text = f"REPUBLIQUE ... {marker_word} ... etc."
        markers = detect_counterfeit_markers(text, {})
        _assert(len(markers) > 0,
                f"Le marqueur '{marker_word}' doit être détecté, got {markers}")
        checks += 1

    # ---- 4. Numéros de pièce évidents ----
    for num in ("00000000", "11111111", "12345678", "IC000000411",
                "TEST12345", "FAKE0001", "DEMO0000"):
        assert _is_suspicious_document_number(num), f"'{num}' doit être suspect"
        checks += 1

    # Numéros de pièce plausibles (pas de patterns triviaux)
    for num in ("C00123456", "CI0234567", "P9081234", "AB1428753"):
        assert not _is_suspicious_document_number(num), f"'{num}' est légitime"
        checks += 1

    # ---- 5. Marqueur dans le nom mais pas dans le texte (edge) ----
    fields_only_ident = {
        "nom": "TEST",
        "prenoms": "USER",
        "numero_piece": "C00123456",
    }
    markers = detect_counterfeit_markers("Document valide", fields_only_ident)
    _assert(any("specimen_in_identity_field" in m for m in markers),
            f"TEST dans le nom doit être signalé, got {markers}")
    checks += 1

    # ---- 6. Case-insensitive : specimen minuscule doit aussi être détecté ----
    markers = detect_counterfeit_markers("this is a specimen document", {})
    _assert(len(markers) > 0,
            "'specimen' minuscule doit être détecté (case-insensitive)")
    checks += 1

    sys.stdout.write(
        f"OK - detection de pieces contrefaites fonctionne ({checks} verifs)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
