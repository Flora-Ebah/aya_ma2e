"""SettingsRegistry — déclaration centralisée des paramètres de la plateforme.

Chaque setting est décrit par un `SettingDescriptor` :
- category : groupement logique (ex. "general", "ocr", "ia")
- key : identifiant unique au sein de la catégorie
- value_type : type primitif
- default : valeur par défaut si non-paramétré en BD
- validator : callable optionnel pour règles métier (range, format, etc.)

L'introduction d'un nouveau paramètre se fait UNIQUEMENT ici. Ça force la
documentation et permet à l'API de retourner aussi le **schéma** au frontend
(le frontend n'a pas besoin de connaître les paramètres à l'avance).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.models.setting import SettingValueType


# ====================================================================== #
# Descriptor
# ====================================================================== #
@dataclass(frozen=True)
class SettingDescriptor:
    """Description déclarative d'un paramètre."""

    category: str
    key: str
    value_type: SettingValueType
    default: Any
    label: str
    description: str = ""
    # Options pour les enums (liste de strings affichables au frontend)
    enum_options: Optional[list[str]] = None
    # Bornes optionnelles pour int/float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    # Longueur max pour strings
    max_length: Optional[int] = None
    # Catégorie de sensibilité — utile pour masquer en frontend (secrets)
    sensitive: bool = False
    # Tags pour grouper visuellement (ex. "Onboarding", "Validation")
    group: Optional[str] = None

    @property
    def full_key(self) -> str:
        """Clé qualifiée 'category.key' (utilisée comme cle de cache)."""
        return f"{self.category}.{self.key}"


# ====================================================================== #
# Registry
# ====================================================================== #
class _SettingsRegistry:
    """Singleton qui regroupe tous les SettingDescriptor."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], SettingDescriptor] = {}
        self._by_category: dict[str, list[SettingDescriptor]] = {}

    def register(self, descriptor: SettingDescriptor) -> None:
        key = (descriptor.category, descriptor.key)
        if key in self._by_key:
            raise ValueError(f"Setting already registered : {descriptor.full_key}")
        self._by_key[key] = descriptor
        self._by_category.setdefault(descriptor.category, []).append(descriptor)

    def get(self, category: str, key: str) -> Optional[SettingDescriptor]:
        return self._by_key.get((category, key))

    def list_category(self, category: str) -> list[SettingDescriptor]:
        return list(self._by_category.get(category, []))

    def categories(self) -> list[str]:
        return sorted(self._by_category.keys())

    def validate(self, descriptor: SettingDescriptor, raw_value: Any) -> Any:
        """Valide et normalise une valeur reçue. Lève ValueError sur erreur."""
        v = raw_value
        t = descriptor.value_type

        if t in (SettingValueType.string, SettingValueType.text):
            if not isinstance(v, str):
                raise ValueError(f"{descriptor.full_key} : string requis (reçu {type(v).__name__})")
            if descriptor.max_length and len(v) > descriptor.max_length:
                raise ValueError(f"{descriptor.full_key} : longueur > {descriptor.max_length}")
            return v

        if t == SettingValueType.integer:
            try:
                v = int(v)
            except (TypeError, ValueError):
                raise ValueError(f"{descriptor.full_key} : integer requis")
            if descriptor.min_value is not None and v < descriptor.min_value:
                raise ValueError(f"{descriptor.full_key} : valeur < min ({descriptor.min_value})")
            if descriptor.max_value is not None and v > descriptor.max_value:
                raise ValueError(f"{descriptor.full_key} : valeur > max ({descriptor.max_value})")
            return v

        if t == SettingValueType.float_:
            try:
                v = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"{descriptor.full_key} : float requis")
            if descriptor.min_value is not None and v < descriptor.min_value:
                raise ValueError(f"{descriptor.full_key} : valeur < min ({descriptor.min_value})")
            if descriptor.max_value is not None and v > descriptor.max_value:
                raise ValueError(f"{descriptor.full_key} : valeur > max ({descriptor.max_value})")
            return v

        if t == SettingValueType.boolean:
            if isinstance(v, bool):
                return v
            if isinstance(v, str) and v.lower() in ("true", "false", "1", "0"):
                return v.lower() in ("true", "1")
            raise ValueError(f"{descriptor.full_key} : boolean requis")

        if t == SettingValueType.enum:
            if descriptor.enum_options is None:
                raise ValueError(f"{descriptor.full_key} : enum sans options déclarées")
            if v not in descriptor.enum_options:
                raise ValueError(
                    f"{descriptor.full_key} : valeur invalide, attendu parmi {descriptor.enum_options}"
                )
            return v

        if t == SettingValueType.json:
            if not isinstance(v, (dict, list)):
                raise ValueError(f"{descriptor.full_key} : object/array JSON requis")
            return v

        raise ValueError(f"{descriptor.full_key} : type inconnu {t}")


# ====================================================================== #
# Instance singleton + déclaration des paramètres MA2E
# ====================================================================== #
registry = _SettingsRegistry()


# ---- Catégorie : general (paramètres globaux MA2E) -------------------- #
registry.register(SettingDescriptor(
    category="general",
    key="assistant_name",
    value_type=SettingValueType.string,
    default="MA2E Assistant",
    label="Nom de l'assistante virtuelle",
    description="Nom affiché de l'assistante virtuelle. Injecté dans les templates et les messages.",
    max_length=64,
    group="Identité",
))

registry.register(SettingDescriptor(
    category="general",
    key="support_phone",
    value_type=SettingValueType.string,
    default="+225 27 20 XX XX XX",
    label="Numéro de support MA2E",
    description="Numéro affiché aux sociétaires pour contacter MA2E directement.",
    max_length=32,
    group="Identité",
))

registry.register(SettingDescriptor(
    category="general",
    key="support_email",
    value_type=SettingValueType.string,
    default="support@ma2e.ci",
    label="Email de support MA2E",
    max_length=128,
    group="Identité",
))

registry.register(SettingDescriptor(
    category="general",
    key="otp_max_attempts",
    value_type=SettingValueType.integer,
    default=3,
    min_value=1,
    max_value=10,
    label="Nombre maximum de tentatives OTP",
    description="Au-delà, le sociétaire doit recommencer la procédure.",
    group="Authentification",
))

registry.register(SettingDescriptor(
    category="general",
    key="otp_validity_minutes",
    value_type=SettingValueType.integer,
    default=10,
    min_value=5,
    max_value=30,
    label="Durée de validité de l'OTP (minutes)",
    group="Authentification",
))

registry.register(SettingDescriptor(
    category="general",
    key="session_max_idle_days",
    value_type=SettingValueType.integer,
    default=7,
    min_value=1,
    max_value=30,
    label="Inactivité avant purge d'une session de conversation (jours)",
    description="Si le sociétaire n'envoie pas de message pendant N jours, sa conversation est réinitialisée.",
    group="Conversation",
))

registry.register(SettingDescriptor(
    category="general",
    key="ocr_min_confidence_score",
    value_type=SettingValueType.float_,
    default=0.7,
    min_value=0.0,
    max_value=1.0,
    label="Score de confiance OCR minimum",
    description="En dessous de ce seuil, le dossier est marqué pour revue manuelle prioritaire.",
    group="OCR",
))

registry.register(SettingDescriptor(
    category="general",
    key="complement_response_deadline_days",
    value_type=SettingValueType.integer,
    default=15,
    min_value=3,
    max_value=60,
    label="Délai max pour fournir un complément demandé (jours)",
    description="Au-delà, le dossier est clôturé automatiquement.",
    group="Validation",
))

registry.register(SettingDescriptor(
    category="general",
    key="support_hours",
    value_type=SettingValueType.string,
    default="Lundi-Vendredi 8h-17h",
    label="Horaires d'ouverture du support",
    description="Affiché aux sociétaires demandant à parler à un conseiller hors heures.",
    max_length=128,
    group="Support",
))

registry.register(SettingDescriptor(
    category="general",
    key="agent_handoff_target_minutes",
    value_type=SettingValueType.integer,
    default=30,
    min_value=5,
    max_value=240,
    label="Délai cible de prise en charge par un agent (minutes)",
    description="Communiqué au sociétaire lors d'une escalade humaine.",
    group="Support",
))

registry.register(SettingDescriptor(
    category="general",
    key="artci_page_url",
    value_type=SettingValueType.string,
    default="https://app.ma2e.ci/artci",
    max_length=512,
    label="URL de la page publique ARTCI",
    description=(
        "Lien vers la page d'information protection des données (US-29). "
        "Injecté dans chaque template via la variable {artci_url}."
    ),
    group="Support",
))

registry.register(SettingDescriptor(
    category="general",
    key="kpi_alert_thresholds",
    value_type=SettingValueType.json,
    default={
        "validation_rate": {"warn": 0.85, "danger": 0.75, "op": "<"},
        "auto_complete_rate": {"warn": 0.70, "danger": 0.50, "op": "<"},
        "avg_validation_hours": {"warn": 24, "danger": 48, "op": ">"},
        "submitted": {"warn": 50, "danger": 100, "op": ">"},
    },
    label="Seuils d'alerte des KPI (US-26 AC3)",
    description=(
        "Seuils par KPI : {warn, danger, op}. op='<' = alerte si valeur passe sous le seuil "
        "(idéal pour les taux). op='>' = alerte si valeur monte au-dessus (idéal pour délais ou backlog). "
        "Les valeurs en taux sont entre 0 et 1."
    ),
    group="Reporting & KPI",
))

registry.register(SettingDescriptor(
    category="general",
    key="rejection_motives",
    value_type=SettingValueType.json,
    default=[
        "Pièce d'identité non conforme ou illisible",
        "Matricule non reconnu par notre référentiel",
        "Sociétaire non éligible (statut employeur)",
        "Doublon avec un dossier existant",
        "Informations incohérentes ou incomplètes",
        "Autre (à préciser dans le motif libre)",
    ],
    label="Motifs de refus prédéfinis",
    description=(
        "Liste des motifs proposés à l'agent lors du refus d'un dossier (US-20). "
        "Le motif libre reste toujours disponible en option « Autre »."
    ),
    group="Validation",
))


# ---- Catégorie : ai (paramétrage du moteur conversationnel LLM) ------- #
#
# Ces paramètres pilotent les appels Groq dans `app/conversation/llm.py` et
# les actions de workflow. Chaque tenant peut ajuster le modèle, le ton et les
# garde-fous sans qu'un développeur intervienne.
#
# Modèles Groq disponibles (à mettre à jour quand la liste évolue côté Groq).
_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

_DEFAULT_PERSONA = (
    "Tu es l'assistante virtuelle de MA2E (Mutuelle des Agents de l'Eau et de l'Électricité, "
    "Côte d'Ivoire). Tu réponds en français, de manière chaleureuse mais professionnelle. "
    "Tu aides les agents employés par CIE, SODECI et ERANOVE à compléter leur dossier "
    "d'identification en ligne. Tu respectes le RGPD et les exigences ARTCI : tu ne demandes "
    "jamais plus d'informations que nécessaire et tu rappelles le droit au retrait du consentement "
    "si on te le demande. Quand tu ne sais pas, tu le dis et tu proposes de transférer la "
    "conversation à un conseiller MA2E."
)

registry.register(SettingDescriptor(
    category="ai",
    key="ai_model",
    value_type=SettingValueType.enum,
    default="llama-3.3-70b-versatile",
    enum_options=_GROQ_MODELS,
    label="Modèle LLM",
    description="Modèle Groq utilisé pour la compréhension et les réponses libres.",
    group="Modèle",
))

registry.register(SettingDescriptor(
    category="ai",
    key="ai_temperature",
    value_type=SettingValueType.float_,
    default=0.3,
    min_value=0.0,
    max_value=2.0,
    label="Température",
    description="0 = déterministe et factuel · 1 = créatif · au-delà = imprévisible.",
    group="Modèle",
))

registry.register(SettingDescriptor(
    category="ai",
    key="ai_max_tokens",
    value_type=SettingValueType.integer,
    default=512,
    min_value=64,
    max_value=4096,
    label="Tokens max par réponse",
    description="Limite la longueur des réponses générées par l'IA (1 token ≈ 0,7 mot).",
    group="Modèle",
))

registry.register(SettingDescriptor(
    category="ai",
    key="ai_max_history_messages",
    value_type=SettingValueType.integer,
    default=10,
    min_value=0,
    max_value=50,
    label="Profondeur d'historique conversationnel",
    description="Nombre de messages précédents transmis au LLM pour assurer la cohérence.",
    group="Modèle",
))

registry.register(SettingDescriptor(
    category="ai",
    key="ai_persona_intro",
    value_type=SettingValueType.text,
    default=_DEFAULT_PERSONA,
    label="Persona de l'assistante",
    description=(
        "Description du rôle, du ton et des règles de comportement de l'assistante. "
        "Ce texte est injecté en tête de chaque prompt système (RAG, escalade, réponses libres)."
    ),
    max_length=4000,
    group="Persona",
))

registry.register(SettingDescriptor(
    category="ai",
    key="ai_response_language",
    value_type=SettingValueType.enum,
    default="fr",
    enum_options=["fr", "en"],
    label="Langue de réponse principale",
    description="Langue cible par défaut. La détection de langue côté entrée reste automatique.",
    group="Persona",
))

registry.register(SettingDescriptor(
    category="ai",
    key="ai_fallback_message",
    value_type=SettingValueType.text,
    default=(
        "Je ne suis pas sûre de bien comprendre votre demande. Pouvez-vous reformuler, "
        "ou tapez *AGENT* pour parler à un conseiller MA2E ?"
    ),
    label="Message de repli (fallback)",
    description="Message envoyé quand l'IA n'arrive pas à répondre avec confiance.",
    max_length=1024,
    group="Persona",
))


# ---- Catégorie : security (politique de sécurité + conformité ARTCI) - #
#
# Centralise les règles de durcissement et de conformité RGPD/ARTCI.
# Chaque tenant peut ajuster sa politique tout en restant au-dessus du
# minimum réglementaire imposé par MA2E (Mutuelle de groupe).

registry.register(SettingDescriptor(
    category="security",
    key="password_min_length",
    value_type=SettingValueType.integer,
    default=12,
    min_value=8,
    max_value=64,
    label="Longueur minimale des mots de passe",
    description=(
        "Politique MA2E (cahier des charges US-01) : 12 caractères minimum, "
        "1 majuscule, 1 chiffre, 1 caractère spécial."
    ),
    group="Mots de passe",
))

registry.register(SettingDescriptor(
    category="security",
    key="password_require_special",
    value_type=SettingValueType.boolean,
    default=True,
    label="Exiger au moins un caractère spécial",
    description="Force la présence d'au moins un caractère parmi !@#$%^&*()_+-=[]{}|;:,.<>?",
    group="Mots de passe",
))

registry.register(SettingDescriptor(
    category="security",
    key="password_require_digit",
    value_type=SettingValueType.boolean,
    default=True,
    label="Exiger au moins un chiffre",
    group="Mots de passe",
))

registry.register(SettingDescriptor(
    category="security",
    key="password_require_uppercase",
    value_type=SettingValueType.boolean,
    default=True,
    label="Exiger au moins une majuscule",
    group="Mots de passe",
))

registry.register(SettingDescriptor(
    category="security",
    key="login_max_failed_attempts",
    value_type=SettingValueType.integer,
    default=5,
    min_value=3,
    max_value=20,
    label="Échecs de login avant verrouillage",
    description="Nombre maximal d'échecs consécutifs avant blocage temporaire du compte.",
    group="Sessions",
))

registry.register(SettingDescriptor(
    category="security",
    key="login_lockout_minutes",
    value_type=SettingValueType.integer,
    default=15,
    min_value=5,
    max_value=1440,
    label="Durée de verrouillage (minutes)",
    description="Délai avant qu'un compte verrouillé puisse retenter une connexion.",
    group="Sessions",
))

registry.register(SettingDescriptor(
    category="security",
    key="session_idle_minutes",
    value_type=SettingValueType.integer,
    default=60,
    min_value=15,
    max_value=480,
    label="Durée d'inactivité avant déconnexion (minutes)",
    description="Une session admin inactive est invalidée après ce délai.",
    group="Sessions",
))

registry.register(SettingDescriptor(
    category="security",
    key="dossier_retention_years",
    value_type=SettingValueType.integer,
    default=5,
    min_value=1,
    max_value=10,
    label="Durée de conservation des dossiers (années)",
    description=(
        "ARTCI art.36 : les données à caractère personnel doivent être conservées "
        "pour une durée n'excédant pas celle nécessaire à la finalité du traitement. "
        "Pour une mutuelle, 5 ans après désinscription est usuel."
    ),
    group="Rétention ARTCI",
))

registry.register(SettingDescriptor(
    category="security",
    key="retention_grace_days",
    value_type=SettingValueType.integer,
    default=30,
    min_value=0,
    max_value=180,
    label="Période de grâce avant purge (jours)",
    description="Délai entre l'échéance de rétention et la purge effective. Permet une revue manuelle.",
    group="Rétention ARTCI",
))

registry.register(SettingDescriptor(
    category="security",
    key="dpo_response_days",
    value_type=SettingValueType.integer,
    default=30,
    min_value=1,
    max_value=90,
    label="Délai de réponse DPO aux demandes de droits (jours)",
    description="ARTCI art.18-22 : le délai légal est de 30 jours, prolongeable de 30 jours sur justification.",
    group="Droits ARTCI",
))

registry.register(SettingDescriptor(
    category="security",
    key="dpo_email",
    value_type=SettingValueType.string,
    default="dpo@ma2e.ci",
    max_length=128,
    label="Email du Délégué à la Protection des Données",
    description="Affiché dans les notices de consentement et utilisé pour les notifications de violation.",
    group="Droits ARTCI",
))

registry.register(SettingDescriptor(
    category="security",
    key="allowed_email_domains",
    value_type=SettingValueType.json,
    default=["ma2e.ci", "eranove.com", "cie.ci", "sodeci.ci"],
    label="Domaines d'email professionnels autorisés",
    description=(
        "Liste des domaines acceptés pour la création d'un utilisateur back-office "
        "(US-04 règle métier : email professionnel du groupe). "
        "Liste vide = aucune restriction."
    ),
    group="Comptes back-office",
))


# ---- Catégorie : integrations (connecteurs externes) ----------------- #
#
# Pilote les intégrations entrantes/sortantes : référentiel agents
# (vérification matricule auprès de CIE/SODECI/ERANOVE) et webhook compta
# (notification du système comptable MA2E à la validation).

registry.register(SettingDescriptor(
    category="integrations",
    key="referential_source",
    value_type=SettingValueType.enum,
    default="none",
    enum_options=["none", "csv", "http"],
    label="Source du référentiel agents",
    description=(
        "none : pas de vérification automatique ; "
        "csv : un CSV statique uploadé par MA2E ; "
        "http : appel à une API distante (ERP CIE/SODECI/ERANOVE)."
    ),
    group="Référentiel agents",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="referential_http_url",
    value_type=SettingValueType.string,
    default="",
    max_length=512,
    label="URL de l'API référentiel (si source = http)",
    description="Endpoint qui retourne {exists, name, status} sur un GET ?employeur=X&matricule=Y.",
    group="Référentiel agents",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="referential_http_token",
    value_type=SettingValueType.string,
    default="",
    max_length=256,
    sensitive=True,
    label="Token Bearer de l'API référentiel",
    description="Authentification de l'appel HTTP. Stocké chiffré côté serveur.",
    group="Référentiel agents",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="referential_strict_mode",
    value_type=SettingValueType.boolean,
    default=False,
    label="Mode strict : rejeter si le matricule n'est pas trouvé",
    description=(
        "Si activé, un dossier dont le matricule n'est pas reconnu dans le "
        "référentiel sera automatiquement marqué pour revue manuelle. "
        "Recommandé pour la production une fois le référentiel stabilisé."
    ),
    group="Référentiel agents",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="compta_webhook_url",
    value_type=SettingValueType.string,
    default="",
    max_length=512,
    label="URL du webhook compta MA2E",
    description=(
        "URL appelée en POST (JSON) lorsqu'un dossier change de statut. "
        "Doit accepter HMAC-SHA256 dans le header `X-MA2E-Signature`."
    ),
    group="Webhook compta",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="compta_webhook_secret",
    value_type=SettingValueType.string,
    default="",
    max_length=128,
    sensitive=True,
    label="Secret HMAC du webhook compta",
    description="Sert à signer les payloads. Doit être > 32 caractères aléatoires.",
    group="Webhook compta",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="compta_webhook_events",
    value_type=SettingValueType.enum,
    default="validated",
    enum_options=["none", "validated", "decided", "all"],
    label="Événements déclenchant le webhook",
    description=(
        "none : aucun ; validated : seulement validation ; "
        "decided : validation + refus ; all : tous les changements de statut."
    ),
    group="Webhook compta",
))

registry.register(SettingDescriptor(
    category="integrations",
    key="webhook_max_retries",
    value_type=SettingValueType.integer,
    default=3,
    min_value=0,
    max_value=10,
    label="Nombre max de tentatives webhook",
    description="Nouvelle tentative en cas d'erreur 5xx ou timeout, avec backoff exponentiel.",
    group="Webhook compta",
))


# ====================================================================== #
# SERVICES — toggles d'activation des intégrations externes
# ====================================================================== #
# Chaque flag détermine si l'action de workflow correspondante s'exécute.
# Quand `false`, l'action retourne immédiatement la branche `disabled` et le
# workflow saute à l'étape suivante définie (voir migration BD).
#
# Lisibles depuis `/parametres/integrations` côté front-office, modifiables
# par tenant_admin / super_admin.
registry.register(SettingDescriptor(
    category="services",
    key="mindee_ocr_enabled",
    value_type=SettingValueType.boolean,
    default=True,
    label="OCR Mindee — extraction des champs CNI",
    description=(
        "Si activé, les photos recto/verso de la pièce d'identité sont analysées "
        "par Mindee + Groq pour extraire automatiquement nom, prénoms, n° de pièce, "
        "MRZ. Si désactivé, le workflow saute les étapes OCR (les photos restent "
        "stockées mais sans extraction)."
    ),
    group="Intégrations externes",
))

registry.register(SettingDescriptor(
    category="services",
    key="email_otp_enabled",
    value_type=SettingValueType.boolean,
    default=True,
    label="Vérification email par OTP",
    description=(
        "Si activé, le sociétaire reçoit un code à 6 chiffres par email pour "
        "confirmer son adresse avant la création du dossier. Si désactivé, "
        "l'étape email est sautée."
    ),
    group="Intégrations externes",
))

registry.register(SettingDescriptor(
    category="services",
    key="notifications_end_enabled",
    value_type=SettingValueType.boolean,
    default=True,
    label="Notification de fin de parcours",
    description=(
        "Si activé, le sociétaire reçoit un récap (WhatsApp + email) avec son "
        "numéro de dossier dès que l'inscription est validée. Si désactivé, "
        "le parcours se termine silencieusement (le numéro reste affiché dans le chat)."
    ),
    group="Intégrations externes",
))

# ─── Sélection du fournisseur OCR (recette / production) ──────────────────
# Permet de basculer entre OCR.space (gratuit, recettes) et Azure AI Vision
# (production) sans redéploiement. Le mock retourne des données fictives,
# utile quand aucune clé OCR n'est disponible.
registry.register(SettingDescriptor(
    category="services",
    key="ocr_provider",
    value_type=SettingValueType.enum,
    default="ocr_space",
    enum_options=["ocr_space", "azure_vision", "mock"],
    label="Fournisseur OCR (recto / verso CNI)",
    description=(
        "Choix du moteur d'extraction de texte sur les photos de pièce d'identité.\n\n"
        "• ocr_space : OCR.space free tier (25k req/mois, 1 MB max — recettes)\n"
        "• azure_vision : Azure AI Vision Read API (production)\n"
        "• mock : données fictives sans appel API (tests offline)\n\n"
        "Dans tous les cas, la structuration du texte en JSON (nom, prénoms, "
        "n° pièce, MRZ…) est faite par Azure OpenAI gpt-5.4-mini."
    ),
    group="Intégrations externes",
))


def get_descriptor(category: str, key: str) -> SettingDescriptor:
    """Helper qui lève KeyError si descriptor inconnu (au lieu de None)."""
    d = registry.get(category, key)
    if d is None:
        raise KeyError(f"Setting non déclaré : {category}.{key}")
    return d
