"""Règle de gestion « longueur des matricules » (backlog v5, tâche 06).

Les matricules des entités du groupe ERANOVE sont alphanumériques ou entièrement numériques.
L'administrateur fixe UN intervalle de longueur COMMUN à toutes les entités (ex. entre 3 et 5
caractères), dans Listes de valeurs → Employeurs du groupe. Il est stocké dans la `config`
de cette liste : {"matricule_min_len": 3, "matricule_max_len": 5}.

Le contrôle porte sur le matricule *normalisé* : majuscules, sans espace, tiret, point,
barre ni underscore (« a-12 34 » compte 5 caractères). Les zéros de tête comptent.
Sans intervalle défini : aucun contrôle (comportement antérieur).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.societaire_import import norm_matricule

MAX_LEN = 64
EMPLOYEURS_KEY = "employeurs"


@dataclass(frozen=True)
class MatriculeRule:
    min_len: Optional[int] = None
    max_len: Optional[int] = None

    @property
    def is_set(self) -> bool:
        return bool(self.min_len or self.max_len)

    def describe(self) -> str:
        """Ex. « entre 3 et 5 caractères »."""
        lo, hi = self.min_len, self.max_len
        if lo and hi:
            return f"{lo} caractère{'s' if lo > 1 else ''}" if lo == hi else f"entre {lo} et {hi} caractères"
        if lo:
            return f"au moins {lo} caractère{'s' if lo > 1 else ''}"
        if hi:
            return f"au plus {hi} caractère{'s' if hi > 1 else ''}"
        return ""


def check_rule(min_len: Optional[int], max_len: Optional[int]) -> None:
    """Lève ValueError (message FR) si l'intervalle est incohérent."""
    for v, nom in ((min_len, "minimum"), (max_len, "maximum")):
        if v is not None and not (1 <= v <= MAX_LEN):
            raise ValueError(f"Le nombre {nom} de caractères doit être compris entre 1 et {MAX_LEN}.")
    if min_len and max_len and min_len > max_len:
        raise ValueError("Le nombre minimum de caractères ne peut pas dépasser le maximum.")


def rule_from_config(config: Optional[dict]) -> MatriculeRule:
    """Règle lue depuis la config de la liste ; une valeur corrompue est ignorée (jamais d'exception)."""
    cfg = config or {}

    def _int(k: str) -> Optional[int]:
        v = cfg.get(k)
        return v if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= MAX_LEN else None

    return MatriculeRule(min_len=_int("matricule_min_len"), max_len=_int("matricule_max_len"))


def matches(rule: Optional[MatriculeRule], matricule: str) -> bool:
    """Vrai si la longueur du matricule (normalisé) est dans l'intervalle ; sans règle : toujours vrai."""
    if rule is None or not rule.is_set:
        return True
    n = len(norm_matricule(matricule) or "")
    if not n:
        return False
    return not (rule.min_len and n < rule.min_len) and not (rule.max_len and n > rule.max_len)


def error_message(matricule: str, rule: MatriculeRule) -> str:
    return f"Le matricule « {matricule} » doit comporter {rule.describe()} (règle commune aux entités du groupe)."


def validate(matricule: str, rule: Optional[MatriculeRule]) -> Optional[str]:
    """None si valide, sinon le message d'erreur à afficher."""
    return None if matches(rule, matricule) else error_message(matricule, rule)


async def load_rule(db: AsyncSession, tenant_id: UUID) -> MatriculeRule:
    """Intervalle commun, lu dans la liste « Employeurs du groupe » du tenant."""
    from app.services.reference_list_service import get_list_by_key

    rl = await get_list_by_key(db, tenant_id, EMPLOYEURS_KEY)
    return rule_from_config(getattr(rl, "config", None) if rl is not None else None)


def chat_error(matricule: str, rule: MatriculeRule) -> Optional[str]:
    """Message du chat quand le matricule saisi n'a pas la bonne longueur (None sinon)."""
    if matches(rule, matricule):
        return None
    return (f"❌ Ce matricule ne correspond pas au format attendu : il doit comporter {rule.describe()}.\n"
            "Vérifiez votre saisie et réessayez.")
