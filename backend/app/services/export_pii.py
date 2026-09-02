"""F-02 (Vague 3) — minimisation des PII dans les exports.

Le rapport pentest v1.0 exige de « réduire au strict nécessaire les données
à caractère personnel présentes dans les exports ». L'export du journal
d'audit contenait `ip_address` et `user_agent` en clair — deux données
identifiantes indirectes qui exposent inutilement les utilisateurs des
comptes MA2E, tout en gardant une utilité forensique très marginale
au-delà des 24-48 premières heures.

Ce module fournit deux helpers d'anonymisation :

- `anonymize_ip(ip)` : IPv4 → masque le dernier octet (192.168.1.42 →
  192.168.1.0/24), IPv6 → masque les 4 derniers groupes (préfixe /64).
  Préserve la géolocalisation approximative sans identifier une machine.

- `sanitize_user_agent(ua)` : garde uniquement le nom du navigateur et
  la version majeure + la famille d'OS. « Mozilla/5.0 (Windows NT 10.0;
  Win64; x64) Chrome/126.0.6478.183 » → « Chrome/126 (Windows) ».

Conformité ARTCI loi 2013-450 : ces sorties ne permettent plus de tracer
un utilisateur individuel à partir de l'export, tout en préservant la
capacité d'agrégation statistique (« 62 % des accès viennent d'un
Chrome sous Windows »).
"""
from __future__ import annotations

import ipaddress
import re


def anonymize_ip(ip: str) -> str:
    """Tronque une adresse IP à un préfixe non-identifiant.

    - IPv4 → /24 (dernier octet à 0)
    - IPv6 → /64 (4 derniers groupes à 0)
    - Chaîne vide, invalide, X-Forwarded-For multi-IPs → chaîne vide

    On reçoit parfois « 1.2.3.4, 5.6.7.8 » (chaînes X-Forwarded-For
    concaténées) — on ne prend que la première.
    """
    if not ip or not isinstance(ip, str):
        return ""
    first = ip.split(",", 1)[0].strip()
    if not first:
        return ""
    try:
        addr = ipaddress.ip_address(first)
    except ValueError:
        return ""
    if isinstance(addr, ipaddress.IPv4Address):
        parts = str(addr).split(".")
        parts[-1] = "0"
        return ".".join(parts) + "/24"
    # IPv6
    net = ipaddress.ip_network(f"{addr}/64", strict=False)
    return str(net)


# --- User-Agent -------------------------------------------------------------
_BROWSER_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    # Ordre important : Edge et Opera avant Chrome (ils contiennent "Chrome").
    (re.compile(r"Edg(?:e|A|iOS)?/(\d+)", re.IGNORECASE), "Edge"),
    (re.compile(r"OPR/(\d+)", re.IGNORECASE), "Opera"),
    (re.compile(r"Firefox/(\d+)", re.IGNORECASE), "Firefox"),
    (re.compile(r"Chrome/(\d+)", re.IGNORECASE), "Chrome"),
    (re.compile(r"Version/(\d+)[^)]*Safari", re.IGNORECASE), "Safari"),
    (re.compile(r"curl/(\d+)", re.IGNORECASE), "curl"),
    (re.compile(r"Postman[\w/]*(\d+)", re.IGNORECASE), "Postman"),
)

_OS_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"Windows NT", re.IGNORECASE), "Windows"),
    (re.compile(r"Mac OS X", re.IGNORECASE), "macOS"),
    (re.compile(r"Linux", re.IGNORECASE), "Linux"),
    (re.compile(r"Android", re.IGNORECASE), "Android"),
    (re.compile(r"iPhone|iPad|iOS", re.IGNORECASE), "iOS"),
)


def sanitize_user_agent(ua: str) -> str:
    """Réduit un User-Agent à une empreinte statistique non identifiante.

    Sortie type : ``"Chrome/126 (Windows)"`` ou ``"curl/8"`` si l'OS n'est
    pas identifiable. Retourne ``""`` si l'entrée est vide/inconnue.
    """
    if not ua or not isinstance(ua, str):
        return ""
    ua = ua.strip()[:256]  # cap défensif

    browser_str = ""
    for pat, name in _BROWSER_PATTERNS:
        m = pat.search(ua)
        if m:
            browser_str = f"{name}/{m.group(1)}"
            break

    os_str = ""
    for pat, name in _OS_PATTERNS:
        if pat.search(ua):
            os_str = name
            break

    if browser_str and os_str:
        return f"{browser_str} ({os_str})"
    if browser_str:
        return browser_str
    if os_str:
        return f"unknown ({os_str})"
    return "unknown"
