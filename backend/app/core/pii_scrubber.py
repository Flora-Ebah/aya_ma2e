"""Masquage des données personnelles (PII) dans les logs applicatifs.

Conforme ARTCI loi 2013-450 : les journaux applicatifs ne doivent pas
conserver de données personnelles identifiantes en clair au-delà du
strict nécessaire au diagnostic technique.

Patterns masqués (ordre d'application, du plus spécifique au plus général) :
- Adresses e-mail        → [EMAIL]
- Numéros CNI ivoiriens  → [CNI]     (format « CI » + 9 chiffres)
- Numéros sociétaires    → [SOC]     (format MA2E-YYYY-NNNNNN)
- Numéros de téléphone   → [PHONE]   (+225 / 00225 / national ivoirien)

Les identifiants techniques (UUID, tokens JWT partiels, IPs) ne sont
PAS masqués — ils sont nécessaires au diagnostic et ne sont pas des
données personnelles au sens strict de l'ARTCI.
"""
from __future__ import annotations

import logging
import re

# ────────────────────────────────────────────────────────────────────────
# Patterns compilés une seule fois (perf)
# ────────────────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_CNI_RE = re.compile(r"\bCI\d{9,10}\b", re.IGNORECASE)
_SOCIETAIRE_RE = re.compile(r"\bMA2E-\d{4}-\d{4,8}\b")
# Téléphones ivoiriens (format 10 chiffres nationaux) ou internationaux +225/00225.
# Les 3 formats les plus courants dans les CNI/dossiers MA2E.
_PHONE_RE = re.compile(
    r"(?:(?:\+|00)225)?[\s.-]?0?[0-9]{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b"
)


def scrub(text: str) -> str:
    """Applique les substitutions de masquage sur une chaîne."""
    if not text or not isinstance(text, str):
        return text
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _CNI_RE.sub("[CNI]", text)
    text = _SOCIETAIRE_RE.sub("[SOC]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    return text


class PIIScrubberFilter(logging.Filter):
    """Filtre stdlib logging qui masque les PII avant émission.

    Applique `scrub()` sur `record.msg` et sur chaque argument positionnel
    (record.args). Ne modifie pas les objets structurés (dict passés en
    `extra`) — ceux-là doivent être nettoyés à la source.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = scrub(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: scrub(v) if isinstance(v, str) else v
                                    for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        scrub(a) if isinstance(a, str) else a for a in record.args
                    )
        except Exception:
            # Un filtre ne doit JAMAIS faire échouer le log lui-même.
            pass
        return True


def scrub_structlog_event(_logger, _method_name, event_dict: dict) -> dict:
    """Processor structlog qui masque les PII dans chaque valeur str du dict."""
    for key, val in list(event_dict.items()):
        if isinstance(val, str):
            event_dict[key] = scrub(val)
    return event_dict
