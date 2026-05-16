from fastapi import APIRouter, Depends

from app.core.tenancy import AuthContext, get_auth_context

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("")
async def get_me(ctx: AuthContext = Depends(get_auth_context)):
    return {
        "user_id": str(ctx.user_id),
        "tenant_id": str(ctx.tenant_id) if ctx.tenant_id else None,
        "role": ctx.role.value,
        "is_super_admin": ctx.is_super_admin,
    }
