"""F-11 — helpers de validation des paramètres de query.

Le rapport pentest v1.0 (finding F-11) a montré que certains filtres
levaient une Internal Server Error 500 quand la valeur reçue n'était
pas reconnue (ex. ``?action=ZZZUNKNOWN`` sur /api/audit/logs ou
``?limit=-1``). C'est un défaut de robustesse : le pentester attend
soit un 400 explicite, soit un résultat vide.

La reco pentester :
  « Uniformiser le traitement des filtres afin qu'une valeur inconnue
    produise un résultat vide plutôt qu'une erreur. »

Ce module centralise ce contrat. Deux helpers :

- ``try_enum(EnumCls, value)`` : renvoie l'instance enum si ``value``
  matche un membre valide, sinon ``None``. Utilisé pour construire
  les filtres SQLAlchemy dynamiquement : si le helper retourne
  ``None``, la route se rabat sur un résultat vide au lieu de laisser
  remonter un ``ValueError``.

- ``UNMATCHABLE_SENTINEL`` : constante à insérer dans un ``.where()``
  pour forcer le résultat à zéro ligne quand un filtre demandé est
  invalide (utile quand on veut garder la structure du query).
"""
from __future__ import annotations

import enum
from typing import Optional, Type, TypeVar

E = TypeVar("E", bound=enum.Enum)


UNMATCHABLE_SENTINEL: str = "__ma2e_unmatchable__"
"""Valeur qu'aucune colonne réelle ne contient. Sert de garde-fou pour
forcer un résultat vide sur un query dont le filtre est invalide."""


def try_enum(enum_cls: Type[E], value: Optional[str]) -> Optional[E]:
    """Convertit ``value`` en membre de l'enum. Renvoie ``None`` si
    ``value`` est ``None`` OU si aucune correspondance n'existe (au lieu
    de laisser remonter un ``ValueError``).

    Match par valeur (``enum_cls(value)``) puis, en dernier ressort, par
    nom (``enum_cls[value.upper()]``). Insensible aux erreurs de casse
    utilisateur sans devenir permissif : seuls les noms/valeurs exacts
    matchent.

    Exemples :
      >>> try_enum(AuditAction, "user_login")
      AuditAction.user_login
      >>> try_enum(AuditAction, "ZZZUNKNOWN")
      None
      >>> try_enum(AuditAction, None)
      None
    """
    if value is None:
        return None
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        pass
    try:
        return enum_cls[value.upper()]
    except (KeyError, AttributeError):
        return None
