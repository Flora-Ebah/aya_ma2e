"""Règle de gestion « matricule à format variable » (backlog v5, tâche 06).

Chaque employeur du groupe a sa propre structure de matricule (longueur, lettres, chiffres…).
L'administrateur la décrit par une EXPRESSION RÉGULIÈRE sur le matricule *normalisé* :
majuscules, sans espace, tiret, point, barre ni underscore (« a-12 34 » est contrôlé comme « A1234 »).
Sans format défini, l'employeur n'est soumis à aucun contrôle (comportement antérieur).
"""
from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.societaire_import import norm_matricule

MAX_PATTERN_LEN = 120
MAX_MATRICULE_LEN = 64
# Quantificateur appliqué à un groupe qui en contient déjà un : (a+)+ , (\w*)* … (explosion combinatoire)
_NESTED_QUANTIFIER = re.compile(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*[+*{]")


def check_pattern(pattern: Optional[str]) -> Optional[str]:
    """Normalise le format saisi. Retourne None si vide ; lève ValueError (message FR) si inutilisable."""
    p = (pattern or "").strip()
    if not p:
        return None
    if len(p) > MAX_PATTERN_LEN:
        raise ValueError(f"Format trop long ({MAX_PATTERN_LEN} caractères maximum).")
    if _NESTED_QUANTIFIER.search(p):
        raise ValueError("Format refusé : quantificateurs imbriqués (risque de blocage). Simplifiez l'expression.")
    try:
        re.compile(p)
    except re.error as e:
        raise ValueError(f"Expression régulière invalide : {e}.")
    return p


def matches(pattern: Optional[str], matricule: str) -> bool:
    """Vrai si le matricule (normalisé) correspond ENTIÈREMENT au format ; sans format : toujours vrai."""
    if not pattern:
        return True
    norm = norm_matricule(matricule)
    if not norm or len(norm) > MAX_MATRICULE_LEN:
        return False
    try:
        return re.fullmatch(pattern, norm, re.IGNORECASE) is not None
    except re.error:
        return False


def error_message(code: str, matricule: str, exemple: Optional[str]) -> str:
    base = f"Le matricule « {matricule} » ne respecte pas le format des matricules {code}"
    return base + (f" (exemple : {exemple})." if exemple else ".")


def validate_for_employeur(matricule: str, code: str, pattern: Optional[str], exemple: Optional[str]) -> Optional[str]:
    """None si valide, sinon le message d'erreur à afficher."""
    return None if matches(pattern, matricule) else error_message(code, matricule, exemple)


async def load_formats(db: AsyncSession, tenant_id: UUID, only_active: bool = False) -> dict[str, tuple[str, Optional[str]]]:
    """{code_employeur: (format, exemple)} pour les employeurs qui ont un format défini."""
    from app.models import Employeur

    stmt = select(Employeur).where(Employeur.tenant_id == tenant_id, Employeur.matricule_format.is_not(None))
    if only_active:
        stmt = stmt.where(Employeur.is_active.is_(True))
    return {
        e.code.upper(): (e.matricule_format, e.matricule_exemple)
        for e in (await db.execute(stmt)).scalars()
        if (e.matricule_format or "").strip()
    }


def known_format_error(matricule: str, formats: dict[str, tuple[str, Optional[str]]]) -> Optional[str]:
    """Pour la saisie dans le chat, où l'employeur n'est pas encore connu : le matricule doit
    respecter AU MOINS UN des formats configurés. None si aucun format n'est configuré ou si l'un convient."""
    if not formats or any(matches(p, matricule) for p, _ in formats.values()):
        return None
    exemples = [f"{code} : {ex}" for code, (_, ex) in sorted(formats.items()) if ex]
    msg = "❌ Ce matricule ne correspond à aucun format connu."
    if exemples:
        msg += "\nExemples de matricules : " + " · ".join(exemples) + "."
    return msg + "\nVérifiez votre saisie et réessayez."

