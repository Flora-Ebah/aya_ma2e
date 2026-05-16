from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=64)
    name: str
    description: Optional[str] = None
    branding: dict = Field(default_factory=dict)
    menu_config: dict = Field(default_factory=dict)
    llm_config: dict = Field(default_factory=dict)


class TenantOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str]
    branding: dict
    menu_config: dict
    is_active: bool

    class Config:
        from_attributes = True


class ChannelCreate(BaseModel):
    channel: str
    external_id: str
    display_name: Optional[str] = None
    credentials: dict
