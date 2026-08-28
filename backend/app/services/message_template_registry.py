"""Registry des codes de templates supportés par MA2E.

Chaque code est associé à :
- la liste des **variables obligatoires** (ex. `{prenom}`, `{nom}`)
- la liste des **variables optionnelles** (présentes ou non)
- le canal cible recommandé (whatsapp, email, web_chat)
- un contenu par défaut (en français)

Ce registry sert à :
1. Valider qu'un template enregistré contient bien les variables obligatoires
2. Fournir un contenu par défaut si pas encore paramétré
3. Documenter les templates disponibles dans l'UI admin (page templates)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.models.message_template import MessageChannel


# Variables auto-injectées dans tous les templates depuis settings.general,
# autorisées par défaut dans n'importe quel template sans déclaration explicite.
# Voir `message_template_service._system_variables`.
SYSTEM_VARIABLES: frozenset[str] = frozenset({
    "assistant_name",
    "support_phone",
    "support_email",
    "support_hours",
    "artci_url",  # URL de la page publique ARTCI (US-29 AC1)
    "dpo_email",  # Email du DPO (depuis settings.security.dpo_email)
})


# Limites de taille par canal (cahier des charges US-06 :
# 1024 chars WhatsApp / 5000 chars email).
CHANNEL_MAX_LENGTH: dict[str, int] = {
    "whatsapp": 1024,
    "sms": 480,
    "email": 5000,
    "web_chat": 5000,
    "any": 5000,
}


def channel_max_length(channel: "MessageChannel") -> int:
    return CHANNEL_MAX_LENGTH.get(channel.value, 5000)


# ====================================================================== #
# Descriptor
# ====================================================================== #
@dataclass(frozen=True)
class MessageTemplateDescriptor:
    code: str
    label: str
    description: str
    channel: MessageChannel
    required_vars: tuple[str, ...] = ()
    optional_vars: tuple[str, ...] = ()
    default_fr: str = ""
    default_subject_fr: Optional[str] = None
    # Catégorie d'affichage dans l'UI admin
    group: str = "Général"
    # Limite caractères (auto-suggérée selon le canal)
    max_length: Optional[int] = None

    @property
    def all_vars(self) -> tuple[str, ...]:
        return tuple(set(self.required_vars + self.optional_vars))


# ====================================================================== #
# Registry
# ====================================================================== #
_VAR_PATTERN = re.compile(r"\{(\w+)\}")


class _MessageTemplateRegistry:
    def __init__(self) -> None:
        self._by_code: dict[str, MessageTemplateDescriptor] = {}

    def register(self, d: MessageTemplateDescriptor) -> None:
        if d.code in self._by_code:
            raise ValueError(f"Template déjà enregistré : {d.code}")
        self._by_code[d.code] = d

    def get(self, code: str) -> Optional[MessageTemplateDescriptor]:
        return self._by_code.get(code)

    def all(self) -> list[MessageTemplateDescriptor]:
        return list(self._by_code.values())

    def groups(self) -> list[str]:
        return sorted({d.group for d in self._by_code.values()})

    def by_group(self, group: str) -> list[MessageTemplateDescriptor]:
        return [d for d in self._by_code.values() if d.group == group]

    def extract_vars(self, content: str) -> set[str]:
        """Extrait toutes les variables `{var}` présentes dans un contenu."""
        return set(_VAR_PATTERN.findall(content or ""))

    def validate_template(
        self,
        descriptor: MessageTemplateDescriptor,
        content: str,
    ) -> None:
        """Lève ValueError si le contenu n'inclut pas toutes les variables obligatoires
        ou utilise une variable non déclarée.

        Les variables système (`assistant_name`, etc.) sont toujours autorisées.
        """
        used = self.extract_vars(content)
        required = set(descriptor.required_vars)
        allowed = set(descriptor.all_vars) | SYSTEM_VARIABLES

        missing = required - used
        if missing:
            raise ValueError(
                f"Variables obligatoires manquantes : {sorted(missing)}"
            )

        unknown = used - allowed
        if unknown:
            raise ValueError(
                f"Variables non déclarées : {sorted(unknown)}. "
                f"Autorisées : {sorted(allowed)}"
            )

        # La limite effective = min(descriptor.max_length, canal limit)
        # — descriptor.max_length impose un plafond explicite si défini, sinon
        # on utilise la limite du canal (1024 WhatsApp / 5000 email-web).
        channel_limit = channel_max_length(descriptor.channel)
        effective_max = min(descriptor.max_length, channel_limit) if descriptor.max_length else channel_limit
        if effective_max and len(content) > effective_max:
            raise ValueError(
                f"Contenu trop long ({len(content)} > {effective_max} caractères "
                f"pour canal {descriptor.channel.value})"
            )

    def render(self, content: str, variables: dict[str, str]) -> str:
        """Substitue les variables dans le contenu.

        F-09 — les gabarits internes non substitués ne doivent pas fuiter
        vers l'utilisateur. Après la substitution des variables connues,
        les tokens `{xxx}` restants sont remplacés par un tiret discret,
        qui signale l'absence sans exposer le nom technique de la variable.
        """
        import re
        out = content
        for name, value in variables.items():
            out = out.replace("{" + name + "}", str(value))
        # Ne matche que les patterns d'identifiant Python valides pour éviter
        # de fusiller des accolades légitimes (JSON, code, …).
        return re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_]{0,63}\}", "—", out)


# ====================================================================== #
# Instance singleton + déclaration des templates MA2E
# ====================================================================== #
template_registry = _MessageTemplateRegistry()


# ---- ONBOARDING ------------------------------------------------------- #
template_registry.register(MessageTemplateDescriptor(
    code="onboarding.welcome",
    label="Message d'accueil",
    description="Premier message reçu par le sociétaire qui démarre une conversation.",
    channel=MessageChannel.whatsapp,
    optional_vars=("prenom",),
    default_fr=(
        "👋 *Bonjour, je suis {assistant_name}, votre assistante MA2E.*\n\n"
        "Je peux vous aider à :\n"
        "1️⃣ Compléter votre dossier d'identification\n"
        "2️⃣ Mettre à jour vos informations\n"
        "3️⃣ Vérifier le statut de votre dossier\n"
        "4️⃣ Poser une question sur MA2E\n\n"
        "Que souhaitez-vous faire ?\n"
        "_Tapez votre choix ou décrivez votre besoin en quelques mots._\n\n"
        "_Vos droits ARTCI : {artci_url}_"
    ),
    group="Onboarding",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="onboarding.ask_matricule",
    label="Demande du matricule",
    description="Demande du matricule après la sélection de la société employeuse.",
    channel=MessageChannel.whatsapp,
    required_vars=("societe",),
    default_fr=(
        "Parfait, vous êtes employé(e) chez *{societe}*.\n\n"
        "Veuillez saisir votre *matricule* (tel qu'il figure sur votre bulletin de salaire)."
    ),
    group="Onboarding",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="onboarding.ask_otp",
    label="Envoi du code OTP par email",
    description="Demande de saisie du code OTP reçu par email.",
    channel=MessageChannel.whatsapp,
    required_vars=("email",),
    default_fr=(
        "Un code de vérification à 6 chiffres a été envoyé à *{email}*.\n"
        "Veuillez le saisir ici (validité : 10 minutes)."
    ),
    group="Onboarding",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="onboarding.ask_cni_recto",
    label="Demande photo CNI recto",
    description="Demande de l'envoi de la photo recto de la CNI.",
    channel=MessageChannel.whatsapp,
    default_fr=(
        "Merci ! Maintenant, envoyez la *photo recto* de votre CNI.\n\n"
        "📷 Conseils :\n"
        "• Posez la pièce sur une surface plane\n"
        "• Bon éclairage\n"
        "• La pièce doit être entièrement visible\n"
        "• Évitez les reflets"
    ),
    group="Onboarding",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="onboarding.ask_cni_verso",
    label="Demande photo CNI verso",
    description="Demande de l'envoi de la photo verso de la CNI.",
    channel=MessageChannel.whatsapp,
    default_fr=(
        "Maintenant la *photo verso* de votre CNI (côté avec la bande MRZ)."
    ),
    group="Onboarding",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="onboarding.confirm_data",
    label="Confirmation des données extraites",
    description="Présentation des données extraites par OCR pour confirmation.",
    channel=MessageChannel.whatsapp,
    required_vars=("nom", "prenoms", "date_naissance", "numero_cni"),
    default_fr=(
        "Voici les données que j'ai extraites de votre CNI :\n\n"
        "• Nom : *{nom}*\n"
        "• Prénoms : *{prenoms}*\n"
        "• Né(e) le : *{date_naissance}*\n"
        "• Numéro CNI : *{numero_cni}*\n\n"
        "Ces informations sont-elles correctes ?\n"
        "→ Répondez *OUI* pour confirmer\n"
        "→ Répondez *NON* pour corriger"
    ),
    group="Onboarding",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="onboarding.success",
    label="Confirmation soumission dossier",
    description="Confirmation finale de la soumission du dossier.",
    channel=MessageChannel.whatsapp,
    required_vars=("numero_dossier",),
    default_fr=(
        "✅ Votre dossier *{numero_dossier}* a bien été enregistré.\n\n"
        "Un agent MA2E va l'examiner. Vous serez notifié(e) ici dès qu'une "
        "décision sera prise (généralement sous 48h ouvrées).\n\n"
        "Merci pour votre confiance 🤝\n\n"
        "_Vos droits sur vos données : {artci_url}_"
    ),
    group="Onboarding",
    max_length=1024,
))


# ---- VALIDATION ------------------------------------------------------- #
template_registry.register(MessageTemplateDescriptor(
    code="validation.dossier_valide",
    label="Notification de validation",
    description="Message envoyé au sociétaire lorsqu'un dossier est validé.",
    channel=MessageChannel.any_,
    required_vars=("numero_dossier",),
    optional_vars=("prenom", "numero_societaire"),
    default_fr=(
        "🎉 Félicitations {prenom} !\n\n"
        "Votre dossier MA2E *{numero_dossier}* vient d'être *validé*.\n"
        "Votre numéro de sociétaire est : *{numero_societaire}*\n\n"
        "Vous êtes désormais officiellement enregistré(e) comme sociétaire MA2E.\n"
        "Pour toute question : support@ma2e.ci\n\n"
        "Merci de votre confiance.\n— Équipe MA2E"
    ),
    group="Validation",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="validation.dossier_refuse",
    label="Notification de refus",
    description="Message envoyé au sociétaire lorsqu'un dossier est refusé.",
    channel=MessageChannel.any_,
    required_vars=("numero_dossier", "motif"),
    optional_vars=("prenom",),
    default_fr=(
        "Bonjour {prenom},\n\n"
        "Votre dossier MA2E *{numero_dossier}* n'a pas pu être validé pour la raison suivante :\n\n"
        "👉 *{motif}*\n\n"
        "Vous pouvez reprendre la conversation pour soumettre un nouveau dossier "
        "en corrigeant les éléments mentionnés, ou contacter le support : support@ma2e.ci\n\n"
        "— Équipe MA2E"
    ),
    group="Validation",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="validation.complement_requested",
    label="Demande de complément",
    description="Message envoyé au sociétaire quand un complément est demandé.",
    channel=MessageChannel.any_,
    required_vars=("numero_dossier", "elements_requis"),
    optional_vars=("prenom",),
    default_fr=(
        "Bonjour {prenom},\n\n"
        "Un complément est requis pour votre dossier MA2E *{numero_dossier}* :\n\n"
        "👉 {elements_requis}\n\n"
        "Répondez directement à ce message pour compléter votre dossier.\n\n"
        "— Équipe MA2E"
    ),
    group="Validation",
    max_length=1024,
))


# ---- ERREURS / ESCALADE ---------------------------------------------- #
template_registry.register(MessageTemplateDescriptor(
    code="error.generic",
    label="Erreur générique",
    description="Message d'erreur générique quand une action ne peut pas être réalisée.",
    channel=MessageChannel.any_,
    default_fr=(
        "Désolé, je rencontre actuellement un problème technique. "
        "Veuillez réessayer dans quelques instants ou contacter le support : "
        "support@ma2e.ci"
    ),
    group="Erreurs",
    max_length=1024,
))

template_registry.register(MessageTemplateDescriptor(
    code="escalation.agent",
    label="Escalade vers un agent humain",
    description="Confirmation au sociétaire que la conversation va être transmise à un agent.",
    channel=MessageChannel.any_,
    optional_vars=("delai_minutes",),
    default_fr=(
        "Je transmets votre demande à un agent MA2E.\n\n"
        "Un conseiller vous répondra dans un délai d'environ {delai_minutes} minutes "
        "pendant les heures ouvrables (Lundi-Vendredi 8h-17h).\n\n"
        "Hors heures ouvrables, vous serez rappelé(e) le prochain jour ouvré."
    ),
    group="Support",
    max_length=1024,
))


def get_template_descriptor(code: str) -> MessageTemplateDescriptor:
    d = template_registry.get(code)
    if d is None:
        raise KeyError(f"Template inconnu : {code}")
    return d
