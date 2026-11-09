from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.services import rbac_service

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("")
async def get_me(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Renvoie le profil de l'utilisateur connecté + ses permissions agrégées.

    Les permissions sont au format {module: {action: bool}} avec :
    - super_admin / tenant_admin → tout à True
    - agent → union des rôles métier attribués
    - viewer / autres → tout à False (lecture seule)

    Le frontend lit `permissions` pour masquer dynamiquement les éléments de
    navigation et désactiver les boutons d'action selon le rôle.
    """
    permissions = await rbac_service.effective_permissions(db, ctx)
    return {
        "user_id": str(ctx.user_id),
        "tenant_id": str(ctx.tenant_id) if ctx.tenant_id else None,
        "role": ctx.role.value,
        "is_super_admin": ctx.is_super_admin,
        "permissions": permissions,
    }
