"""API CRUD collaborateurs (référentiel ERANOVE).

Endpoints :
    GET    /api/collaborateurs                 → liste paginée + recherche
    GET    /api/collaborateurs/stats           → chiffres du référentiel + de la base MA2E importée
    GET    /api/collaborateurs/search          → recherche paginée (total, filtres, tri)
    GET    /api/collaborateurs/export.csv      → export CSV (mêmes filtres), ré-importable
    GET    /api/collaborateurs/historique      → historique des actions (imports, exports, ajouts, modifications, retraits)
    GET    /api/collaborateurs/{id}            → détail
    POST   /api/collaborateurs                 → création
    PATCH  /api/collaborateurs/{id}            → mise à jour
    DELETE /api/collaborateurs/{id}            → suppression
    GET    /api/collaborateurs/lookup          → vérification matricule (utilisé par anti-fraude)
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Integer, String, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import AuditAction, AuditLog, Collaborateur, Employeur, Societaire, User, UserRole
from app.services import audit_service
from app.services.matricule_format import load_rule, validate as validate_matricule
from app.services.societaire_import import norm_matricule

router = APIRouter(prefix="/api/collaborateurs", tags=["collaborateurs"])


# ====================================================================== #
# Schémas
# ====================================================================== #
class CollaborateurOut(BaseModel):
    id: UUID
    tenant_id: UUID
    matricule: str
    employeur_code: str
    nom: str
    prenoms: str
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    fonction: Optional[str] = None
    date_embauche: Optional[date] = None
    statut: str

    model_config = ConfigDict(from_attributes=True)


class CollaborateurCreateIn(BaseModel):
    matricule: str = Field(min_length=1, max_length=32)
    employeur_code: str = Field(min_length=1, max_length=32)
    nom: str = Field(min_length=1, max_length=255)
    prenoms: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telephone: Optional[str] = Field(default=None, max_length=32)
    fonction: Optional[str] = Field(default=None, max_length=255)
    date_embauche: Optional[date] = None
    statut: str = Field(default="actif", max_length=32)


class CollaborateurUpdateIn(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=255)
    prenoms: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telephone: Optional[str] = Field(default=None, max_length=32)
    fonction: Optional[str] = Field(default=None, max_length=255)
    date_embauche: Optional[date] = None
    statut: Optional[str] = Field(default=None, max_length=32)


# ====================================================================== #
# Helpers
# ====================================================================== #
def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(status_code=403, detail="Accès admin requis.")


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


async def _audit(db: AsyncSession, ctx: AuthContext, tenant_id: UUID, action: AuditAction,
                 collab_id: UUID, details: dict) -> None:
    await audit_service.log(
        db, tenant_id=tenant_id, action=action, resource_type="collaborateur",
        resource_id=str(collab_id), actor_type="user", actor_id=str(ctx.user_id), details=details,
    )


# ====================================================================== #
# Endpoints
# ====================================================================== #
@router.get("", response_model=list[CollaborateurOut])
async def list_collaborateurs(
    employeur_code: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Recherche dans matricule, nom, prénoms, email"),
    statut: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    stmt = (
        select(Collaborateur)
        .where(Collaborateur.tenant_id == tenant_id)
        .order_by(Collaborateur.nom.asc(), Collaborateur.prenoms.asc())
        .limit(limit)
    )
    if employeur_code:
        stmt = stmt.where(Collaborateur.employeur_code == employeur_code)
    if statut:
        stmt = stmt.where(Collaborateur.statut == statut)
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(or_(
            Collaborateur.matricule.ilike(q),
            Collaborateur.nom.ilike(q),
            Collaborateur.prenoms.ilike(q),
            Collaborateur.email.ilike(q),
        ))
    return list((await db.execute(stmt)).scalars().all())


STATUTS = ("actif", "retraite", "demission", "licencie", "inactif")

SORTS = {
    "nom": (Collaborateur.nom.asc(), Collaborateur.prenoms.asc(), Collaborateur.matricule.asc()),
    "matricule": (Collaborateur.matricule.asc(), Collaborateur.employeur_code.asc()),
    "employeur": (Collaborateur.employeur_code.asc(), Collaborateur.nom.asc(), Collaborateur.prenoms.asc()),
    "recent": (Collaborateur.created_at.desc(), Collaborateur.matricule.asc()),
}


def search_filters(tenant_id: UUID, q: Optional[str], employeur_code: Optional[str], statut: Optional[str]) -> list:
    """Conditions communes à la liste paginée et à l'export (mêmes lignes, mêmes filtres)."""
    where = [Collaborateur.tenant_id == tenant_id]
    if employeur_code:
        where.append(Collaborateur.employeur_code == employeur_code.upper())
    if statut:
        where.append(Collaborateur.statut == statut)
    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        conds = [
            Collaborateur.matricule.ilike(like),
            Collaborateur.nom.ilike(like),
            Collaborateur.prenoms.ilike(like),
            Collaborateur.email.ilike(like),
            Collaborateur.fonction.ilike(like),
            func.concat(Collaborateur.nom, " ", Collaborateur.prenoms).ilike(like),
            func.concat(Collaborateur.prenoms, " ", Collaborateur.nom).ilike(like),
        ]
        nm = norm_matricule(term)
        if nm:  # « t 001 » retrouve « T-001 » : casse, espaces et séparateurs ignorés
            conds.append(func.upper(func.regexp_replace(Collaborateur.matricule, r"[\s\-_./]", "", "g")) == nm)
        where.append(or_(*conds))
    return where


CSV_COLUMNS = ["matricule", "employeur_code", "nom", "prenoms", "email", "telephone", "fonction", "date_embauche", "statut"]
EXPORT_MAX_ROWS = 100_000


def csv_cell(v) -> str:
    """Valeur de cellule CSV sûre : anti « injection de formule » (=, +, -, @ en tête sont lus comme
    une formule par Excel), séparateur `;` et guillemets protégés."""
    if v is None:
        return ""
    s = v.isoformat() if hasattr(v, "isoformat") else str(v)
    s = s.replace("\r", " ").replace("\n", " ")
    if s[:1] in ("=", "+", "-", "@", "\t"):
        s = "'" + s
    if any(c in s for c in (';', '"')):
        s = '"' + s.replace('"', '""') + '"'
    return s


HISTORY_RESOURCES = ("collaborateur", "import:collaborateurs", "export:collaborateurs")
_CHAMPS_LIBELLES = {
    "nom": "nom", "prenoms": "prénoms", "email": "e-mail", "telephone": "téléphone",
    "fonction": "fonction", "date_embauche": "date d'embauche", "statut": "statut",
}
_STATUT_LIBELLES = {"actif": "Actif", "retraite": "Retraité", "demission": "Démission",
                    "licencie": "Licencié", "inactif": "Inactif"}


def describe_action(resource_type: str, action: str, d: dict) -> tuple[str, str, str]:
    """(type, libellé, détail) lisibles d'une ligne du journal d'audit."""
    d = d or {}
    if resource_type == "import:collaborateurs":
        f = d.get("filename") or "fichier"
        ok, ko, total = d.get("accepted") or 0, d.get("rejected") or 0, d.get("total_lines") or 0
        if ok:
            return "import", f"Import du fichier « {f} »", f"{ok} matricule{'s' if ok > 1 else ''} ajouté{'s' if ok > 1 else ''} sur {total} ligne{'s' if total > 1 else ''}"
        return "import_refuse", f"Import refusé du fichier « {f} »", \
            f"{ko} ligne{'s' if ko > 1 else ''} en erreur : aucun matricule n'a été ajouté"
    if resource_type == "export:collaborateurs":
        n = d.get("lignes") or 0
        filtres = [f"{k} = {v}" for k, v in (("recherche", d.get("q")), ("employeur", d.get("employeur_code")),
                                              ("statut", d.get("statut"))) if v]
        return "export", "Export CSV de la liste", \
            f"{n} ligne{'s' if n > 1 else ''}" + (f" · filtres : {', '.join(filtres)}" if filtres else "")
    m, emp = d.get("matricule") or "?", d.get("employeur_code") or ""
    cible = f"{m} ({emp})" if emp else m
    if action == "referentiel_added":
        return "ajout", f"Ajout du matricule {cible}", ""
    if action == "referentiel_removed":
        return "retrait", f"Retrait du matricule {cible}", ""
    champs = ", ".join(_CHAMPS_LIBELLES.get(c, c) for c in d.get("champs") or [])
    detail = f"Champs modifiés : {champs}" if champs else ""
    st = d.get("statut")
    if st:
        detail += f" · statut : {_STATUT_LIBELLES.get(st.get('de'), st.get('de'))} → {_STATUT_LIBELLES.get(st.get('vers'), st.get('vers'))}"
    return "modification", f"Modification du matricule {cible}", detail


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Chiffres affichés en tête de la fenêtre « Référentiel des sociétaires ERANOVE » et dans la
    liste des valeurs : taille du référentiel, répartition par employeur, dernier import, et
    taille de la base MA2E importée (qui, elle, se consulte dans « Dossiers »).

    Déclarée AVANT `/{collab_id}` : sinon « stats » serait lu comme un identifiant.
    """
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    total, actifs = (await db.execute(
        select(func.count(), func.count().filter(Collaborateur.statut == "actif"))
        .where(Collaborateur.tenant_id == tenant_id)
    )).one()
    par_employeur = (await db.execute(
        select(Collaborateur.employeur_code, func.count())
        .where(Collaborateur.tenant_id == tenant_id)
        .group_by(Collaborateur.employeur_code)
        .order_by(desc(func.count()), Collaborateur.employeur_code)
    )).all()

    # Dernier import qui a réellement inséré des lignes (un import refusé n'en insère aucune)
    last = (await db.execute(
        select(AuditLog.created_at, AuditLog.details)
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.resource_type == "import:collaborateurs",
            AuditLog.details["accepted"].astext.cast(Integer) > 0,
        )
        .order_by(desc(AuditLog.created_at))
        .limit(1)
    )).first()

    base_total, base_last = (await db.execute(
        select(func.count(), func.max(Societaire.imported_at)).where(Societaire.tenant_id == tenant_id)
    )).one()

    return {
        "total": total,
        "actifs": actifs,
        "par_employeur": [{"code": c, "total": n} for c, n in par_employeur],
        "dernier_import": (
            {
                "date": last[0].isoformat(),
                "fichier": (last[1] or {}).get("filename"),
                "lignes": (last[1] or {}).get("accepted"),
            } if last else None
        ),
        "base_ma2e": {
            "total": base_total,
            "dernier_import": base_last.isoformat() if base_last else None,
        },
    }


@router.get("/search")
async def search(
    q: Optional[str] = Query(None, max_length=100, description="Matricule, nom, prénoms, e-mail ou fonction"),
    employeur_code: Optional[str] = Query(None, max_length=32),
    statut: Optional[str] = Query(None, pattern="^(actif|retraite|demission|licencie|inactif)$"),
    sort: str = Query("nom", pattern="^(nom|matricule|employeur|recent)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste paginée côté serveur (la liste simple `GET ""` est plafonnée et ne donne pas le total)."""
    _require_admin(ctx)
    where = search_filters(_resolve_tenant(ctx), q, employeur_code, statut)
    total = (await db.execute(select(func.count()).select_from(Collaborateur).where(*where))).scalar_one()
    rows = (await db.execute(
        select(Collaborateur).where(*where).order_by(*SORTS[sort])
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {
        "items": [CollaborateurOut.model_validate(r).model_dump(mode="json") for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export.csv")
async def export_csv(
    q: Optional[str] = Query(None, max_length=100),
    employeur_code: Optional[str] = Query(None, max_length=32),
    statut: Optional[str] = Query(None, pattern="^(actif|retraite|demission|licencie|inactif)$"),
    sort: str = Query("nom", pattern="^(nom|matricule|employeur|recent)$"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Export CSV des matricules filtrés. Mêmes colonnes que le modèle d'import : on peut le ré-importer.
    Donnée personnelle (noms, e-mails, téléphones) : l'export est tracé dans le journal d'audit."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    where = search_filters(tenant_id, q, employeur_code, statut)
    rows = (await db.execute(
        select(Collaborateur).where(*where).order_by(*SORTS[sort]).limit(EXPORT_MAX_ROWS)
    )).scalars().all()
    lines = [";".join(CSV_COLUMNS)] + [
        ";".join(csv_cell(getattr(r, c)) for c in CSV_COLUMNS) for r in rows
    ]
    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.data_export,
        resource_type="export:collaborateurs", resource_id="csv",
        actor_type="user", actor_id=str(ctx.user_id),
        details={"lignes": len(rows), "q": q, "employeur_code": employeur_code, "statut": statut},
    )
    await db.commit()
    return Response(
        content="\ufeff" + "\r\n".join(lines) + "\r\n",   # BOM : Excel lit les accents en UTF-8
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="referentiel-matricules-eranove.csv"'},
    )


@router.get("/historique")
async def historique(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Historique des actions faites dans le référentiel : imports (acceptés ou refusés), exports CSV,
    ajouts, modifications et retraits — du plus récent au plus ancien, avec leur auteur.

    Source : journal d'audit (append-only). Les ajouts / modifications / retraits ne sont tracés que
    depuis l'ajout de cette fonction ; les imports et exports le sont depuis le début.
    """
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    where = [AuditLog.tenant_id == tenant_id, AuditLog.resource_type.in_(HISTORY_RESOURCES)]
    total = (await db.execute(select(func.count()).select_from(AuditLog).where(*where))).scalar_one()
    rows = (await db.execute(
        select(AuditLog, User.name, User.email)
        .outerjoin(User, cast(User.id, String) == AuditLog.actor_id)
        .where(*where)
        .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
        .offset((page - 1) * page_size).limit(page_size)
    )).all()
    items = []
    for log, name, email in rows:
        kind, libelle, detail = describe_action(log.resource_type, log.action.value, log.details)
        items.append({
            "id": str(log.id),
            "date": log.created_at.isoformat(),
            "type": kind,
            "libelle": libelle,
            "detail": detail,
            "auteur": name or email or ("Système" if log.actor_type != "user" else "Utilisateur supprimé"),
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/lookup")
async def lookup(
    employeur_code: str = Query(...),
    matricule: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Vérifie qu'un matricule existe dans le référentiel.
    Réponse compatible avec referential_service (same shape)."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (
        await db.execute(
            select(Collaborateur).where(
                Collaborateur.tenant_id == tenant_id,
                Collaborateur.employeur_code == employeur_code.strip().upper(),
                Collaborateur.matricule == matricule.strip(),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {
            "found": False,
            "matricule": matricule,
            "employeur": employeur_code,
            "source": "internal",
        }
    return {
        "found": True,
        "matricule": row.matricule,
        "employeur": row.employeur_code,
        "name": f"{row.nom} {row.prenoms}".strip(),
        "fonction": row.fonction,
        "status": row.statut,
        "source": "internal",
    }


@router.get("/{collab_id}", response_model=CollaborateurOut)
async def get_collaborateur(
    collab_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.id == collab_id,
            Collaborateur.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    return row


@router.post("", response_model=CollaborateurOut, status_code=201)
async def create_collaborateur(
    payload: CollaborateurCreateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    # Unicité
    existing = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.tenant_id == tenant_id,
            Collaborateur.employeur_code == payload.employeur_code.upper(),
            Collaborateur.matricule == payload.matricule,
        )
    )).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Le matricule {payload.matricule} existe déjà pour {payload.employeur_code}.",
        )
    # Longueur des matricules : intervalle commun à toutes les entités du groupe
    msg = validate_matricule(payload.matricule, await load_rule(db, tenant_id))
    if msg:
        raise HTTPException(status_code=422, detail=msg)
    row = Collaborateur(
        tenant_id=tenant_id,
        matricule=payload.matricule.strip(),
        employeur_code=payload.employeur_code.strip().upper(),
        nom=payload.nom.strip(),
        prenoms=payload.prenoms.strip(),
        email=payload.email,
        telephone=payload.telephone,
        fonction=payload.fonction,
        date_embauche=payload.date_embauche,
        statut=payload.statut,
    )
    db.add(row)
    await db.flush()
    await _audit(db, ctx, tenant_id, AuditAction.referentiel_added, row.id,
                 {"matricule": row.matricule, "employeur_code": row.employeur_code})
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/{collab_id}", response_model=CollaborateurOut)
async def update_collaborateur(
    collab_id: UUID,
    payload: CollaborateurUpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.id == collab_id,
            Collaborateur.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    changed: list[str] = []
    statut_avant = row.statut
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field in ("nom", "prenoms", "statut"):
            continue  # colonnes obligatoires : ignorer un « null » plutôt que lever une erreur 500
        if getattr(row, field) != value:
            changed.append(field)
        setattr(row, field, value)
    if changed:  # rien n'a réellement changé : rien à tracer
        # Journal en ajout seul : on y met le matricule et les NOMS des champs modifiés, jamais leurs valeurs
        # (noms, e-mails, téléphones) — seul le statut, non personnel, est détaillé.
        details = {"matricule": row.matricule, "employeur_code": row.employeur_code, "champs": changed}
        if "statut" in changed:
            details["statut"] = {"de": statut_avant, "vers": row.statut}
        await _audit(db, ctx, tenant_id, AuditAction.referentiel_updated, row.id, details)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{collab_id}", status_code=204)
async def delete_collaborateur(
    collab_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.id == collab_id,
            Collaborateur.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    await _audit(db, ctx, tenant_id, AuditAction.referentiel_removed, row.id,
                 {"matricule": row.matricule, "employeur_code": row.employeur_code})
    await db.delete(row)
    await db.commit()
