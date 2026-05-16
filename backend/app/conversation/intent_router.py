"""Routeur d'intention 100% LLM-driven (Groq Llama 3.3 70B).

Pas de regex hardcodés : AYA comprend les intentions par contexte naturel.
Latence ~300 ms par message, mais compréhension réelle de toutes les formulations.

Intents :
- identification → démarrer parcours identification
- update         → mise à jour d'infos
- status         → vérification de statut
- question       → question libre sur MA2E (déclenche RAG)
- droits         → exercer ses droits (ARTCI art.18-22)
- cancel         → annuler / quitter
- menu           → afficher le menu principal
- greeting       → salutation / nouvelle conversation
- flow_input     → valeur attendue par le parcours en cours (nom, adresse, matricule…)
- other          → fallback ambigu
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from app.conversation.llm import chat_complete

log = logging.getLogger(__name__)


INTENT_DEFINITIONS = """
- identification : VOLONTÉ D'ACTION IMMÉDIATE pour s'inscrire / s'enrôler / créer son dossier / devenir membre. Le sociétaire veut DÉMARRER le processus maintenant. Exemples : "Je veux m'inscrire", "Je voudrais devenir membre", "Inscrivez-moi", "Démarrons l'inscription".
- update         : VOLONTÉ D'ACTION pour modifier ses informations. "Je veux changer", "Je dois corriger", "Mettez à jour".
- status         : Le sociétaire veut connaître l'état d'avancement de son dossier (validé ? en attente ?).
- question       : Toute DEMANDE D'INFORMATION sur MA2E. Inclut les questions sur le processus d'inscription ("Comment s'inscrire ?", "Que faut-il pour adhérer ?"), les produits, prestations, crédits, épargne, droits, fonctionnement, coordonnées, frais, conditions, etc. RÈGLE CRITIQUE : si la phrase commence par un mot interrogatif (Comment, Que, Quoi, Quels, Où, Pourquoi, Combien, Est-ce que) OU contient "?", c'est presque toujours une 'question', PAS une 'identification' / 'update' / 'status'.
- droits         : Le sociétaire veut exercer ses droits RGPD/ARTCI (accès, rectification, suppression).
- cancel         : Volonté d'annuler / arrêter / abandonner / recommencer.
- menu           : Demande explicite du menu principal / accueil / options.
- greeting       : Salutation pure et simple sans demande spécifique derrière.
- flow_input     : Donnée attendue par un formulaire : nom complet, matricule (chiffres), adresse, profession, date, "oui"/"non", numéro 1/2/3...
- other          : Aucune des intentions ci-dessus.
""".strip()


FEW_SHOT_EXAMPLES = """
Exemples :

Message: "Bonjour AYA, je suis sociétaire MA2E"
→ {"intent": "greeting", "confidence": 0.95, "rationale": "salutation sans demande spécifique"}

Message: "Bonjour, j'aimerais avoir le statut de mon dossier"
→ {"intent": "status", "confidence": 0.95, "rationale": "demande explicite du statut malgré la salutation"}

Message: "Salut, comment puis-je obtenir un crédit immobilier ?"
→ {"intent": "question", "confidence": 0.95, "rationale": "question sur un produit MA2E"}

Message: "Je voudrais m'inscrire à la mutuelle"
→ {"intent": "identification", "confidence": 0.95, "rationale": "volonté d'action : démarrer inscription"}

Message: "Comment m'inscrire à MA2E ?"
→ {"intent": "question", "confidence": 0.95, "rationale": "question sur le processus, pas volonté d'agir tout de suite"}

Message: "Comment intégrer MA2E ?"
→ {"intent": "question", "confidence": 0.95, "rationale": "Comment + topic = question sur le processus"}

Message: "Comment ça marche pour devenir membre ?"
→ {"intent": "question", "confidence": 0.95, "rationale": "demande d'explication, pas d'action immédiate"}

Message: "Que faut-il pour adhérer ?"
→ {"intent": "question", "confidence": 0.95, "rationale": "question sur les conditions"}

Message: "Quels sont les produits d'épargne ?"
→ {"intent": "question", "confidence": 0.95, "rationale": "question sur les prestations"}

Message: "Je veux changer mon numéro de téléphone"
→ {"intent": "update", "confidence": 0.95, "rationale": "mise à jour d'une info"}

Message: "Stop, annule tout"
→ {"intent": "cancel", "confidence": 0.95, "rationale": "annulation explicite"}

Message: "AFFO ADELE FLORA EBAH"
→ {"intent": "flow_input", "confidence": 0.95, "rationale": "ressemble à un nom complet attendu par le parcours"}

Message: "467738"
→ {"intent": "flow_input", "confidence": 0.95, "rationale": "matricule numérique"}

Message: "Yopougon Cocody"
→ {"intent": "flow_input", "confidence": 0.85, "rationale": "ressemble à une adresse"}

Message: "1"
→ {"intent": "flow_input", "confidence": 0.95, "rationale": "choix de menu numéroté"}

Message: "Bonjour, ça va ?"
→ {"intent": "greeting", "confidence": 0.9, "rationale": "salutation conviviale sans demande"}

Message: "ok"
→ {"intent": "flow_input", "confidence": 0.8, "rationale": "confirmation courte"}
""".strip()


@dataclass
class Intent:
    name: str
    confidence: float
    rationale: str = ""


async def detect_intent(message: str, tenant_name: str = "MA2E") -> Intent:
    """Détection d'intention 100% LLM avec few-shot prompting.

    Le LLM voit la liste des intentions + exemples + le message, et retourne JSON.
    """
    msg = (message or "").strip()
    if not msg:
        return Intent(name="other", confidence=0.0, rationale="empty")

    system = (
        f"Tu es le classificateur d'intentions pour AYA, l'assistante virtuelle de {tenant_name} "
        f"(Mutuelle des Agents de l'Eau et de l'Électricité, Côte d'Ivoire).\n\n"
        f"Tu reçois un message du sociétaire et tu dois identifier son intention principale "
        f"parmi cette liste fermée :\n\n"
        f"{INTENT_DEFINITIONS}\n\n"
        f"Règles importantes :\n"
        f"1. Une salutation accompagnée d'une demande explicite → classe selon la demande, "
        f"   PAS comme 'greeting' (ex: 'Bonjour, je veux mon statut' → status).\n"
        f"2. Une salutation pure et simple sans demande → 'greeting'.\n"
        f"3. Les saisies courtes sans verbe (noms, chiffres, adresses, oui/non) → 'flow_input'.\n"
        f"4. Si la phrase contient un mot interrogatif (quoi, comment, qui, quel, où, "
        f"   pourquoi, combien) ou un point d'interrogation → souvent 'question'.\n"
        f"5. Ne JAMAIS inventer une nouvelle intention hors de la liste.\n\n"
        f"{FEW_SHOT_EXAMPLES}\n\n"
        f"Réponds UNIQUEMENT en JSON valide, exactement ce format :\n"
        f'{{"intent": "<key>", "confidence": <0.0-1.0>, "rationale": "<phrase courte>"}}'
    )

    try:
        raw = await chat_complete(system_prompt=system, user_message=msg)
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            return Intent(
                name=str(data.get("intent", "other")),
                confidence=float(data.get("confidence", 0.0)),
                rationale=str(data.get("rationale", "")),
            )
    except Exception as e:
        log.warning("intent llm failed: %s", e)
    return Intent(name="other", confidence=0.0, rationale="llm fallback")
