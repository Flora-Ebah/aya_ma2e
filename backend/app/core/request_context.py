"""Context-local de la requête HTTP courante (IP, user-agent).

Permet à n'importe quel service profond (audit, webhook…) de récupérer le
contexte de la requête sans avoir à le propager à toutes les signatures.

Rempli par `RequestContextMiddleware` dans `app/main.py`.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass
class RequestContext:
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


_current: ContextVar[RequestContext] = ContextVar(
    "request_context", default=RequestContext()
)


def current() -> RequestContext:
    return _current.get()


def set_current(ctx: RequestContext) -> None:
    _current.set(ctx)
