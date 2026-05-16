from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PieceOut(BaseModel):
    id: UUID
    piece_type: str
    face: str
    storage_key: str
    ocr_status: str
    ocr_data: dict
    mrz_data: dict
    ocr_confidence: Optional[float]
    user_corrections: dict
    created_at: datetime

    class Config:
        from_attributes = True


class DonneesProOut(BaseModel):
    fonction: Optional[str]
    anciennete_annees: Optional[int]
    situation_familiale: Optional[str]
    nombre_ayants_droit: int

    class Config:
        from_attributes = True


class ConsentementOut(BaseModel):
    id: UUID
    gate: str
    decision: str
    texte_version: str
    signature: str
    channel: str
    created_at: datetime

    class Config:
        from_attributes = True


class DossierListItem(BaseModel):
    id: UUID
    dossier_number: str
    status: str
    matricule: Optional[str]
    employeur_code: Optional[str]
    end_user_name: Optional[str] = None
    end_user_contact: Optional[str] = None
    submitted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEntryOut(BaseModel):
    id: UUID
    action: str
    actor_type: str
    actor_id: Optional[str]
    details: dict
    created_at: datetime

    class Config:
        from_attributes = True


class DossierDetail(BaseModel):
    id: UUID
    tenant_id: UUID
    dossier_number: str
    status: str
    matricule: Optional[str]
    employeur_code: Optional[str]
    rejection_motive: Optional[str]
    additional_request: Optional[str]
    submitted_at: Optional[datetime]
    validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    pieces: list[PieceOut]
    donnees_pro: Optional[DonneesProOut]
    consentements: list[ConsentementOut]
    end_user: dict
    audit_logs: list[dict] = []

    class Config:
        from_attributes = True


class ValidateRequest(BaseModel):
    pass


class RejectRequest(BaseModel):
    motive: str


class ComplementRequest(BaseModel):
    request_text: str
