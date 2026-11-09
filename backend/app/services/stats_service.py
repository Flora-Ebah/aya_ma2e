"""Service de statistiques et reporting MA2E.

Calculs agrégés directement en SQL (pas de chargement de tous les rows).
Toutes les requêtes sont tenant-scoped et acceptent un filtre de période.

Retour : structures sérialisables JSON, dataclasses pour clarté.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Channel,
    Conversation,
    Dossier,
    DossierStatus,
    Message,
    PieceIdentite,
    User,
)

logger = logging.getLogger(__name__)


# ====================================================================== #
# Dataclasses
# ====================================================================== #
@dataclass
class KPIDelta:
    """Variation en valeur absolue et en pourcentage d'un KPI par rapport
    à la période précédente (US-26 AC2)."""
    current: float
    previous: float
    delta: float
    delta_pct: Optional[float]  # None si previous = 0

    @staticmethod
    def of(current: float, previous: float) -> "KPIDelta":
        delta = current - previous
        if previous != 0:
            delta_pct = round((delta / previous) * 100, 1)
        else:
            delta_pct = None
        return KPIDelta(
            current=current,
            previous=previous,
            delta=round(delta, 2),
            delta_pct=delta_pct,
        )


@dataclass
class OverviewKPIs:
    period_days: int
    total_dossiers: int
    total_period: int  # créés dans la période
    submitted: int
    validated: int
    rejected: int
    complement_requested: int
    in_progress: int
    validation_rate: float  # validated / (validated + rejected)
    avg_validation_hours: Optional[float]
    auto_complete_rate: float  # validated sans complément / submitted
    total_conversations: int
    total_messages: int
    # US-26 AC2 — comparaison à la période précédente (None si pas demandée)
    deltas: Optional[dict] = None  # {kpi_name: KPIDelta.__dict__}
    # US-26 AC3 — alertes calculées contre les seuils configurés
    alerts: Optional[list[dict]] = None  # [{kpi, threshold, value, severity}]


@dataclass
class TimelineBucket:
    date: str  # YYYY-MM-DD
    created: int
    validated: int
    rejected: int


@dataclass
class ChannelStat:
    channel: str
    dossiers: int
    conversations: int
    share_pct: float


@dataclass
class RejectionReason:
    motive: str
    count: int
    share_pct: float


@dataclass
class AgentPerformance:
    agent_id: str
    agent_name: str
    validated: int
    rejected: int
    complement_requested: int
    total_decisions: int


@dataclass
class OcrQualityStat:
    average_confidence: Optional[float]
    high_quality_pct: float    # >= 0.8
    medium_quality_pct: float  # 0.5-0.8
    low_quality_pct: float     # < 0.5
    total_pieces: int


@dataclass
class ConversionFunnel:
    conversations_started: int
    dossiers_created: int
    dossiers_submitted: int
    dossiers_validated: int
    started_to_created_pct: float
    created_to_submitted_pct: float
    submitted_to_validated_pct: float
    overall_pct: float


# ====================================================================== #
# Helpers
# ====================================================================== #
def _period_start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# ====================================================================== #
# Overview KPIs
# ====================================================================== #
async def get_overview(
    db: AsyncSession,
    tenant_id: UUID,
    period_days: int = 30,
    compare_previous: bool = True,
    alert_thresholds: Optional[dict] = None,
) -> OverviewKPIs:
    """KPIs globaux pour le dashboard exécutif (US-24, US-26).

    - `compare_previous=True` (US-26 AC2) calcule aussi les valeurs sur la
      période précédente de même durée et expose les variations dans `deltas`.
    - `alert_thresholds` (US-26 AC3) : dict {kpi_name: {warn: x, danger: y}}
      pour évaluer les alertes.
    """
    period_start = _period_start(period_days)

    # Comptes par statut (toutes périodes confondues)
    by_status_rows = (
        await db.execute(
            select(Dossier.status, func.count(Dossier.id))
            .where(Dossier.tenant_id == tenant_id)
            .group_by(Dossier.status)
        )
    ).all()
    by_status = {s.value: 0 for s in DossierStatus}
    for st, n in by_status_rows:
        by_status[st.value] = n

    total = sum(by_status.values())

    # Créés dans la période
    total_period = (
        await db.execute(
            select(func.count(Dossier.id)).where(
                Dossier.tenant_id == tenant_id,
                Dossier.created_at >= period_start,
            )
        )
    ).scalar_one()

    # Temps moyen de validation (en heures, sur les dossiers validés de la période)
    avg_hours_row = (
        await db.execute(
            select(
                func.avg(
                    func.extract("epoch", Dossier.validated_at - Dossier.submitted_at) / 3600.0
                )
            ).where(
                Dossier.tenant_id == tenant_id,
                Dossier.status == DossierStatus.valide,
                Dossier.validated_at.is_not(None),
                Dossier.submitted_at.is_not(None),
                Dossier.validated_at >= period_start,
            )
        )
    ).scalar_one_or_none()
    avg_validation_hours = float(avg_hours_row) if avg_hours_row is not None else None

    # Taux validation = valid / (valid + reject)
    validated = by_status["valide"]
    rejected = by_status["rejete"]
    validation_rate = (
        validated / (validated + rejected) if (validated + rejected) > 0 else 0.0
    )

    # Auto-complétion = validés sans demande de complément / soumis (approximation)
    submitted_or_above = (
        by_status["soumis"]
        + by_status["en_validation"]
        + by_status["valide"]
        + by_status["rejete"]
        + by_status["complement_requis"]
    )
    auto_complete_rate = (
        validated / submitted_or_above if submitted_or_above > 0 else 0.0
    )

    # Conversations et messages (période)
    total_conversations = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.tenant_id == tenant_id,
                Conversation.created_at >= period_start,
            )
        )
    ).scalar_one()

    total_messages = (
        await db.execute(
            select(func.count(Message.id)).where(
                Message.tenant_id == tenant_id,
                Message.created_at >= period_start,
            )
        )
    ).scalar_one()

    # === US-26 AC2 — comparaison à la période précédente ===
    deltas_dict: Optional[dict] = None
    if compare_previous:
        prev_end = period_start
        prev_start = prev_end - timedelta(days=period_days)
        # 4 KPIs comparables : total_period, validated_period, rejected_period, conversations
        prev_total_period = (
            await db.execute(
                select(func.count(Dossier.id)).where(
                    Dossier.tenant_id == tenant_id,
                    Dossier.created_at >= prev_start,
                    Dossier.created_at < prev_end,
                )
            )
        ).scalar_one() or 0
        prev_validated = (
            await db.execute(
                select(func.count(Dossier.id)).where(
                    Dossier.tenant_id == tenant_id,
                    Dossier.status == DossierStatus.valide,
                    Dossier.validated_at >= prev_start,
                    Dossier.validated_at < prev_end,
                )
            )
        ).scalar_one() or 0
        prev_rejected = (
            await db.execute(
                select(func.count(Dossier.id)).where(
                    Dossier.tenant_id == tenant_id,
                    Dossier.status == DossierStatus.rejete,
                    Dossier.validated_at >= prev_start,
                    Dossier.validated_at < prev_end,
                )
            )
        ).scalar_one() or 0
        prev_conversations = (
            await db.execute(
                select(func.count(Conversation.id)).where(
                    Conversation.tenant_id == tenant_id,
                    Conversation.created_at >= prev_start,
                    Conversation.created_at < prev_end,
                )
            )
        ).scalar_one() or 0
        prev_messages = (
            await db.execute(
                select(func.count(Message.id)).where(
                    Message.tenant_id == tenant_id,
                    Message.created_at >= prev_start,
                    Message.created_at < prev_end,
                )
            )
        ).scalar_one() or 0
        prev_validation_rate = (
            prev_validated / (prev_validated + prev_rejected)
            if (prev_validated + prev_rejected) > 0 else 0.0
        )
        deltas_dict = {
            "total_period": KPIDelta.of(total_period, prev_total_period).__dict__,
            "validated_period": KPIDelta.of(validated, prev_validated).__dict__,
            "rejected_period": KPIDelta.of(rejected, prev_rejected).__dict__,
            "validation_rate": KPIDelta.of(validation_rate, prev_validation_rate).__dict__,
            "total_conversations": KPIDelta.of(total_conversations, prev_conversations).__dict__,
            "total_messages": KPIDelta.of(total_messages, prev_messages).__dict__,
        }

    # === US-26 AC3 — alertes selon seuils configurés ===
    alerts_list: Optional[list[dict]] = None
    if alert_thresholds:
        alerts_list = []
        kpi_values: dict[str, float] = {
            "validation_rate": validation_rate,
            "auto_complete_rate": auto_complete_rate,
            "avg_validation_hours": float(avg_validation_hours) if avg_validation_hours else 0.0,
            "in_progress": float(by_status["en_cours"]),
            "submitted": float(by_status["soumis"] + by_status["en_validation"]),
            "total_period": float(total_period),
        }
        # Dénominateurs utilisés pour chaque KPI ratio. Une alerte sur un taux
        # ne se déclenche QUE si on a au moins un dossier dans le dénominateur
        # — sinon 0/0 = "0%" artificiel qui déclenche faussement des alertes
        # critiques alors qu'il n'y a tout simplement aucune donnée à juger.
        kpi_denominators: dict[str, int] = {
            "validation_rate": validated + rejected,
            "auto_complete_rate": submitted_or_above,
            "avg_validation_hours": validated,
        }
        for kpi_name, thresholds in alert_thresholds.items():
            if kpi_name not in kpi_values:
                continue
            # Skip silencieux si c'est un ratio sans données mesurables
            if kpi_denominators.get(kpi_name, 1) == 0:
                continue
            v = kpi_values[kpi_name]
            warn = thresholds.get("warn")
            danger = thresholds.get("danger")
            comparator = thresholds.get("op", "<")  # "<", ">"
            severity = None
            triggered = None
            if comparator == "<":
                if danger is not None and v < float(danger):
                    severity = "danger"; triggered = float(danger)
                elif warn is not None and v < float(warn):
                    severity = "warning"; triggered = float(warn)
            elif comparator == ">":
                if danger is not None and v > float(danger):
                    severity = "danger"; triggered = float(danger)
                elif warn is not None and v > float(warn):
                    severity = "warning"; triggered = float(warn)
            if severity:
                alerts_list.append({
                    "kpi": kpi_name,
                    "value": round(v, 2),
                    "threshold": triggered,
                    "op": comparator,
                    "severity": severity,
                })

    return OverviewKPIs(
        period_days=period_days,
        total_dossiers=total,
        total_period=total_period,
        submitted=by_status["soumis"] + by_status["en_validation"],
        validated=validated,
        rejected=rejected,
        complement_requested=by_status["complement_requis"],
        in_progress=by_status["en_cours"],
        validation_rate=round(validation_rate, 3),
        avg_validation_hours=round(avg_validation_hours, 1) if avg_validation_hours else None,
        auto_complete_rate=round(auto_complete_rate, 3),
        total_conversations=total_conversations,
        total_messages=total_messages,
        deltas=deltas_dict,
        alerts=alerts_list,
    )


# ====================================================================== #
# Timeline (création / validation / refus par jour)
# ====================================================================== #
async def get_timeline(
    db: AsyncSession,
    tenant_id: UUID,
    period_days: int = 30,
) -> list[TimelineBucket]:
    period_start = _period_start(period_days)
    period_start_date = period_start.date()

    # Créations par jour
    created_rows = (
        await db.execute(
            select(
                func.date_trunc("day", Dossier.created_at).label("day"),
                func.count(Dossier.id).label("n"),
            )
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.created_at >= period_start,
            )
            .group_by("day")
        )
    ).all()
    created_map = {row.day.date().isoformat(): row.n for row in created_rows}

    # Validations par jour
    validated_rows = (
        await db.execute(
            select(
                func.date_trunc("day", Dossier.validated_at).label("day"),
                func.count(Dossier.id).label("n"),
            )
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.validated_at >= period_start,
                Dossier.status == DossierStatus.valide,
            )
            .group_by("day")
        )
    ).all()
    validated_map = {row.day.date().isoformat(): row.n for row in validated_rows}

    # Rejets par jour
    rejected_rows = (
        await db.execute(
            select(
                func.date_trunc("day", Dossier.validated_at).label("day"),
                func.count(Dossier.id).label("n"),
            )
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.validated_at >= period_start,
                Dossier.status == DossierStatus.rejete,
            )
            .group_by("day")
        )
    ).all()
    rejected_map = {row.day.date().isoformat(): row.n for row in rejected_rows}

    # Construit la timeline complète (incluant les jours zéro)
    buckets: list[TimelineBucket] = []
    for i in range(period_days):
        d = (period_start_date + timedelta(days=i)).isoformat()
        buckets.append(
            TimelineBucket(
                date=d,
                created=created_map.get(d, 0),
                validated=validated_map.get(d, 0),
                rejected=rejected_map.get(d, 0),
            )
        )
    return buckets


# ====================================================================== #
# Répartition par canal
# ====================================================================== #
async def get_by_channel(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[ChannelStat]:
    # Dossiers par canal d'origine (via la conversation rattachée)
    rows = (
        await db.execute(
            select(
                Conversation.channel.label("ch"),
                func.count(distinct(Dossier.id)).label("dossiers"),
                func.count(distinct(Conversation.id)).label("convs"),
            )
            .select_from(Conversation)
            .outerjoin(Dossier, Dossier.conversation_id == Conversation.id)
            .where(Conversation.tenant_id == tenant_id)
            .group_by(Conversation.channel)
        )
    ).all()

    total_dossiers = sum(r.dossiers for r in rows)
    out = []
    for r in rows:
        share = (r.dossiers / total_dossiers) if total_dossiers > 0 else 0.0
        out.append(
            ChannelStat(
                channel=r.ch.value if r.ch else "unknown",
                dossiers=r.dossiers,
                conversations=r.convs,
                share_pct=round(share * 100, 1),
            )
        )
    # Tri par volume desc
    out.sort(key=lambda x: x.dossiers, reverse=True)
    return out


# ====================================================================== #
# Motifs de refus
# ====================================================================== #
async def get_rejection_reasons(
    db: AsyncSession,
    tenant_id: UUID,
    top_n: int = 10,
) -> list[RejectionReason]:
    rows = (
        await db.execute(
            select(
                Dossier.rejection_motive.label("motive"),
                func.count(Dossier.id).label("n"),
            )
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.status == DossierStatus.rejete,
                Dossier.rejection_motive.is_not(None),
            )
            .group_by(Dossier.rejection_motive)
            .order_by(func.count(Dossier.id).desc())
            .limit(top_n)
        )
    ).all()

    total = sum(r.n for r in rows)
    return [
        RejectionReason(
            motive=r.motive or "(non précisé)",
            count=r.n,
            share_pct=round((r.n / total * 100), 1) if total > 0 else 0.0,
        )
        for r in rows
    ]


# ====================================================================== #
# Performance des agents (top traiteurs)
# ====================================================================== #
async def get_agents_performance(
    db: AsyncSession,
    tenant_id: UUID,
    period_days: int = 90,
    top_n: int = 10,
) -> list[AgentPerformance]:
    period_start = _period_start(period_days)

    rows = (
        await db.execute(
            select(
                User.id.label("uid"),
                User.name.label("uname"),
                func.sum(case((Dossier.status == DossierStatus.valide, 1), else_=0)).label("v"),
                func.sum(case((Dossier.status == DossierStatus.rejete, 1), else_=0)).label("r"),
                func.sum(case((Dossier.status == DossierStatus.complement_requis, 1), else_=0)).label("c"),
                func.count(Dossier.id).label("n"),
            )
            .select_from(User)
            .join(Dossier, Dossier.validated_by == User.id)
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.validated_at >= period_start,
            )
            .group_by(User.id, User.name)
            .order_by(func.count(Dossier.id).desc())
            .limit(top_n)
        )
    ).all()

    return [
        AgentPerformance(
            agent_id=str(r.uid),
            agent_name=r.uname,
            validated=int(r.v or 0),
            rejected=int(r.r or 0),
            complement_requested=int(r.c or 0),
            total_decisions=int(r.n or 0),
        )
        for r in rows
    ]


# ====================================================================== #
# Qualité OCR
# ====================================================================== #
async def get_ocr_quality(
    db: AsyncSession,
    tenant_id: UUID,
    period_days: int = 90,
) -> OcrQualityStat:
    period_start = _period_start(period_days)

    rows = (
        await db.execute(
            select(PieceIdentite.ocr_confidence)
            .where(
                PieceIdentite.tenant_id == tenant_id,
                PieceIdentite.ocr_confidence.is_not(None),
                PieceIdentite.created_at >= period_start,
            )
        )
    ).all()
    scores = [float(r[0]) for r in rows if r[0] is not None]

    if not scores:
        return OcrQualityStat(
            average_confidence=None,
            high_quality_pct=0.0,
            medium_quality_pct=0.0,
            low_quality_pct=0.0,
            total_pieces=0,
        )

    n = len(scores)
    avg = sum(scores) / n
    high = sum(1 for s in scores if s >= 0.8)
    med = sum(1 for s in scores if 0.5 <= s < 0.8)
    low = sum(1 for s in scores if s < 0.5)
    return OcrQualityStat(
        average_confidence=round(avg, 3),
        high_quality_pct=round(high / n * 100, 1),
        medium_quality_pct=round(med / n * 100, 1),
        low_quality_pct=round(low / n * 100, 1),
        total_pieces=n,
    )


# ====================================================================== #
# Entonnoir de conversion
# ====================================================================== #
async def get_conversion_funnel(
    db: AsyncSession,
    tenant_id: UUID,
    period_days: int = 30,
) -> ConversionFunnel:
    period_start = _period_start(period_days)

    conv_count = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.tenant_id == tenant_id,
                Conversation.created_at >= period_start,
            )
        )
    ).scalar_one()

    created = (
        await db.execute(
            select(func.count(Dossier.id)).where(
                Dossier.tenant_id == tenant_id,
                Dossier.created_at >= period_start,
            )
        )
    ).scalar_one()

    submitted = (
        await db.execute(
            select(func.count(Dossier.id)).where(
                Dossier.tenant_id == tenant_id,
                Dossier.created_at >= period_start,
                Dossier.submitted_at.is_not(None),
            )
        )
    ).scalar_one()

    validated = (
        await db.execute(
            select(func.count(Dossier.id)).where(
                Dossier.tenant_id == tenant_id,
                Dossier.created_at >= period_start,
                Dossier.status == DossierStatus.valide,
            )
        )
    ).scalar_one()

    def _pct(n: int, d: int) -> float:
        return round(n / d * 100, 1) if d > 0 else 0.0

    return ConversionFunnel(
        conversations_started=conv_count,
        dossiers_created=created,
        dossiers_submitted=submitted,
        dossiers_validated=validated,
        started_to_created_pct=_pct(created, conv_count),
        created_to_submitted_pct=_pct(submitted, created),
        submitted_to_validated_pct=_pct(validated, submitted),
        overall_pct=_pct(validated, conv_count),
    )
