"""Extraction LLM d'un parcours conversationnel depuis un document libre.

L'utilisateur rédige un document Word / PDF / texte avec le titre du parcours
et la liste des questions (ou champs à collecter), dans l'ordre. Le LLM
reconstruit un `ParcoursDocument` structuré : code technique, type d'étape,
validation (regex, format), chaînage next_step_code, messages d'accueil/
récap/completion.

Le flux attendu est : extraction → preview côté UI → correction manuelle
possible → apply (le JSON corrigé est renvoyé tel quel, pas re-extrait).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import llm_azure
from app.models.reference_list import ReferenceList
from app.services import reference_list_service
from app.services.parcours_schema import ParcoursDocument, document_from_dict

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu es un ingénieur conversationnel pour la plateforme MA2E (identification numérique, Côte d'Ivoire).

Tu reçois un document libre (Word ou PDF) qui décrit un parcours à faire jouer par un chatbot WhatsApp/Web. Le document contient typiquement :
- un titre (ex : « Inscription sociétaire », « Mise à jour de compte »),
- la liste des questions ou champs à collecter, souvent numérotés (1. Nom, 2. Prénoms, 3. Date de naissance …).

OBJECTIF UX ESSENTIEL : réduire le nombre d'interactions sur WhatsApp. Au lieu de poser 20 questions une par une (abandons massifs), tu dois GROUPER les champs texte en UN SEUL step de type « question » avec un FORMULAIRE que l'utilisateur copie, remplit et renvoie en un seul message. Seuls les uploads (photos pièce d'identité, signature) restent un par un, et quelques champs sensibles (OTP, consentement, confirmation finale).

RÈGLES DE SORTIE — tu renvoies **UNIQUEMENT** un objet JSON valide, sans texte autour, sans ```json. Structure exacte :

{
  "meta": {"name": "<titre>", "description": "<1 phrase>", "language": "fr"},
  "steps": [
    {
      "order": 1,
      "code": "<snake_case, unique>",
      "label": "<libellé court — titre affiché en tête du formulaire>",
      "description": "<1 phrase courte expliquant à l'utilisateur ce qui est demandé à cette étape, affichée en sous-titre sous le titre du formulaire>",
      "type": "message" | "question" | "action",
      "question": "<texte posé à l'utilisateur, null si type=message/action>",
      "template_code": "<ma2e.XXX>",
      "action_name": "<nom de l'action backend, null sauf si type=action>",
      "next_step_code": "<code de l'étape suivante, null si c'est la dernière>",
      "branches": {},
      "validation_rules": {
        "rules": [{"type": "<regex|min_len|max_len|format>", "value": "<valeur>", "message": "<message d'erreur>"}],
        "form_fields": [{"key": "<snake>", "label": "<Libellé affiché>", "regex": "<optionnel>", "format": "<optionnel: date|email>", "optional": false, "message": "<msg erreur optionnel>"}]
      }
    }
  ],
  "messages": {
    "ma2e.welcome": "Bonjour, bienvenue sur MA2E...",
    "ma2e.completion": "Votre demande est enregistrée. Référence : {dossier_number}"
  }
}

RÈGLES MÉTIER :

1. **Toujours commencer** par une étape type=message code=welcome avec template ma2e.welcome qui dit bonjour, explique en 1 phrase le parcours et annonce le temps estimé.

2. **Toujours terminer** par une étape type=message code=completion avec template ma2e.completion, et next_step_code=null.

3. **CŒUR DE L'OPTIMISATION — étapes « form_XXX » :** regroupe les champs texte en 1 à 3 étapes type=question qui envoient chacune un formulaire à copier/remplir en un seul message. **TU DÉCIDES combien de forms créer selon le volume** :

   - **≤ 10 lignes de texte** → 1 seul form (`form_identite`, identité + contact).
   - **10 à 15 lignes** → 2 forms thématiques : `form_identite` (civilité, nom, naissance, situation, profession) + `form_contact_pro` (téléphone, email, matricule, domicile, employeur).
   - **> 15 lignes** → 3 forms : `form_identite` + `form_contact_pro` + `form_famille` (conjoint, mère, personne à prévenir, ayant droit, chacun en `optional=true`).

   Dans tous les cas, le texte de chaque form suit ce format :

```
Étape X — copiez le modèle ci-dessous, remplissez-le et renvoyez-le en UN SEUL message :

Nom :
Prénoms :
Date de naissance (JJ/MM/AAAA) :
...
```

   Et tu renseignes `validation_rules.form_fields` avec un objet par ligne du formulaire (key = snake_case, label = ce qui précède les deux-points, regex/format/optional selon le type).

   **Important** : un form NE DOIT CONTENIR QUE des champs texte. Les uploads, OTP, consentement, confirmation sont TOUJOURS des steps séparés.

6. **Uploads = UN par UN** : pièce d'identité recto, pièce d'identité verso, signature manuscrite restent chacun un step type=question SANS form_fields (le moteur gère l'upload). Jamais de regroupement d'uploads.

6bis. **PIÈCE D'IDENTITÉ — BLOC COMPLET OBLIGATOIRE** : chaque fois qu'un parcours concerne l'identification d'une personne (inscription, mise à jour d'identité, vérification), tu DOIS insérer la séquence COMPLÈTE des 4 steps ci-dessous, dans cet ordre, même si le document source ne mentionne qu'une partie :

   (a) **form_piece_identite** — type=question avec un form de 2 champs :
       - `{key: "type_piece_identite", label: "Type de pièce d'identité", options_ref: "types_piece_identite"}`
       - `{key: "numero_piece_identite", label: "Numéro de la pièce", regex: "^[A-Z0-9]{6,15}$", message: "Numéro invalide (6-15 lettres/chiffres majuscules)"}`

   (b) **piece_identite_recto** — type=question, label="Photo recto de la pièce", description="Prenez en photo le recto de votre pièce d'identité.", SANS form_fields, SANS options_ref, SANS regex (le moteur attend un upload image via media_url).

   (c) **piece_identite_verso** — type=question, label="Photo verso de la pièce", description="Prenez en photo le verso de votre pièce d'identité.", SANS form_fields, SANS options_ref, SANS regex.

   (d) **signature** — type=question, label="Signature manuscrite", description="Signez dans la zone prévue ou importez une image de votre signature.", SANS form_fields, SANS options_ref, SANS regex (le front affiche un pad de dessin).

   Les codes DOIVENT contenir les mots `recto`, `verso`, `signature` respectivement — le moteur identifie le type de pièce via ces mots-clés. Ne regroupe JAMAIS recto+verso dans un même step. Ne saute JAMAIS la signature pour un parcours d'inscription. Chaîne ces 4 steps consécutivement avec next_step_code.

7. **Déduction des règles de validation** :
   - « nom », « prénoms », « lieu de naissance », « profession », « domicile », « fonction », « service » → texte libre (pas de regex).
   - « matricule » → regex `^[A-Z0-9]{3,12}$`, message « Matricule invalide (3-12 lettres/chiffres majuscules) ». NE JAMAIS lier un matricule à un référentiel — c'est une donnée saisie, pas une liste.
   - « téléphone », « cellulaire », « contact » → regex `^(\\+225)?[0-9]{10}$`, message « Numéro invalide (10 chiffres, format +225...) ».
   - « email » → format=email, message « Adresse email invalide ».
   - « date de naissance », « date d'embauche », toute « date » → format=date, message « Format JJ/MM/AAAA attendu ».
   - « CNI », « pièce d'identité », « passeport » (numéro) → regex `^[A-Z0-9]{6,15}$`.
   - « civilité » → regex `^(M|Mme|Mlle)$`.
   - « situation matrimoniale » → regex `^(Célibataire|Marié|Marié\\(e\\)|Divorcé|Divorcé\\(e\\)|Veuf|Veuf\\(ve\\))$`.

7ter. **CHAMPS FACULTATIFS — DÉTECTION OBLIGATOIRE** : dans le document source, certains champs sont marqués explicitement « facultatif », « optionnel », « (facultatif) », « (optionnel) », « (si applicable) », « (le cas échéant) », « *facultatif* », « non obligatoire », entre parenthèses après le libellé, en italique ou en note de bas de page. Pour CHACUN de ces champs, tu dois mettre `optional: true` dans son form_field. Pour les champs sans marqueur → `optional: false` (défaut). Le libellé final que tu renvoies dans `label` doit être NETTOYÉ de ces mentions (pas « Conjoint (facultatif) » → mets « Conjoint » et `optional: true`). Exemples typiques qui sont presque toujours facultatifs : conjoint, enfants, ayant droit, personne à prévenir, deuxième téléphone, email secondaire, surnom. Prends le temps de relire chaque libellé du document pour attraper les indices discrets.

7bis. **LABEL + DESCRIPTION DE CHAQUE STEP** : chaque step doit avoir un `label` court (2-4 mots, ex: « Informations personnelles », « Vérification OTP », « Pièce d'identité recto ») qui sert de titre, ET une `description` d'1 phrase (max 15 mots) qui explique à l'utilisateur ce qui va se passer à cette étape et pourquoi, ex: « Merci de renseigner votre état civil pour créer votre dossier. » Le front affiche label + description en tête de chaque formulaire côté chat web. Ne laisse JAMAIS `description` vide pour un step de type question — c'est ce qui donne du contexte à l'utilisateur.

8. **RÉFÉRENTIELS FERMÉS — LIAISON OBLIGATOIRE :** certains champs du formulaire ne sont PAS libres mais correspondent à des listes de valeurs déjà gérées en base. Pour ces champs, tu DOIS ajouter dans l'objet `form_fields[i]` une clé `options_ref` qui vaut la `key` du référentiel correspondant (voir liste injectée plus bas dans ce prompt). N'ajoute AUCUN regex sur ces champs : la validation sera faite côté backend contre la liste.

   Exemple de field lié :
   ```json
   {"key": "civilite", "label": "Civilité", "options_ref": "civilites"}
   {"key": "situation_matrimoniale", "label": "Situation matrimoniale", "options_ref": "situations_matrimoniales"}
   ```

   De la même manière, pour une étape type=question hors form (ex. consent, confirm, choix de pièce), tu peux poser `validation_rules.options_ref` au niveau du step.

9. **OTP** : juste après le step form_contact, insère type=action action_name=send_otp, puis type=question code=verify_otp avec regex `^[0-9]{6}$`.

10. **Consentement ARTCI** : si le document mentionne RGPD / ARTCI / consentement / données personnelles, insère APRÈS welcome une étape type=question code=consent_artci avec `options_ref: "reponses_oui_non"` (pas de regex).

11. **MISE À JOUR / MODIFICATION — STRUCTURE IMPOSÉE** : si le titre OU la description OU le corps du document contient « mise à jour », « modifier », « modification », « actualiser », « changer », « corriger », « mettre à jour », le parcours NE DOIT PAS REDEMANDER TOUS LES CHAMPS comme une inscription. La structure OBLIGATOIRE est exactement :

   a) `consent_artci` (type=question, options_ref=reponses_oui_non) — consentement ARTCI
   b) `ask_matricule` (type=question SEUL, SANS form_fields, regex `^[A-Z0-9]{3,12}$`) — on demande uniquement le matricule
   c) `lookup_societaire` (type=action, action_name=lookup_societaire) — récupère le dossier existant depuis la BD. Tu DOIS inclure `"branches": {"not_found": "ask_matricule"}` pour rebrancher sur la demande de matricule en cas d'échec (le code de branche est `not_found`, pas `on_notfound` ni autre).
   d) `choix_modification` (type=question) — **MULTI-SELECT obligatoire** : mets `"validation_rules": {"multi_select": [{"code":"coordonnees","label":"Coordonnées"},{"code":"employeur","label":"Employeur"},{"code":"situation","label":"Situation matrimoniale"},{"code":"piece","label":"Pièce d'identité"}], "min_selected": 1}`. L'utilisateur coche ce qu'il veut modifier. Le backend stocke la sélection dans `ctx.choix_modification_items = [...]`.
   e) Pour CHAQUE domaine ci-dessous, insère les step(s) correspondant(s) ; mets `"meta": {"show_when": {"key": "choix_modification_items", "in": "<code>"}}` sur chaque step pour qu'il soit **exécuté uniquement si le code est coché** :
      - `form_coordonnees` (type=question, form_fields: téléphone, email, domicile, boîte postale) → meta.show_when = {key:"choix_modification_items", in:"coordonnees"}
      - `form_employeur` (type=question, form_fields: employeur[options_ref=employeurs], categorie[options_ref=categories_professionnelles], matricule, direction) → show_when in:"employeur"
      - `ask_situation_matri` (type=question, options_ref=situations_matrimoniales) → show_when in:"situation"
      - `form_piece_identite` + `piece_identite_recto` + `piece_identite_verso` + `signature` → chacun avec show_when in:"piece"
   f) `build_recap` (type=action)
   g) `confirm` (type=question, options_ref=reponses_oui_non)
   h) `save_dossier` (type=action, action_name=create_real_dossier — qui en mode update patche le dossier existant au lieu d'en créer un nouveau)
   i) `completion` (type=message)

   INTERDICTIONS pour un parcours de mise à jour :
   - PAS de form_identite (civilité, nom, prénoms, dates, etc.) — ces données sont déjà en base
   - PAS de form_contact_pro complet
   - PAS de form_famille
   - **PAS de send_otp / verify_otp** : la vérification repose UNIQUEMENT sur le matricule saisi + le lookup_societaire. Pas d'OTP email ni SMS.
   - En gros : on NE repose QUE les questions correspondant au champ que l'utilisateur veut modifier.

   Si tu crées un parcours de mise à jour avec form_identite, OTP, ou plus de 3 forms, le parcours est considéré invalide.

12. **Récap + confirm** avant completion : type=action action_name=build_recap, puis type=question code=confirm avec `options_ref: "reponses_oui_non"`.

12bis. **ENREGISTREMENT DU DOSSIER — OBLIGATOIRE** : immédiatement APRÈS le step `confirm` (si la réponse "OUI" est validée) et AVANT le step `completion`, tu DOIS insérer une étape type=action, code=save_dossier, action_name=create_real_dossier. C'est cette action qui persiste le dossier en base et génère le `{dossier_number}` que le template completion affiche. Sans elle, l'utilisateur reçoit « Référence : — » et aucun dossier n'apparaît dans la console admin. Le chaînage attendu : build_recap → confirm → save_dossier → completion. Si tu omets ce step, le parcours est considéré invalide.

13. **Chaînage** : chaque étape pointe vers la suivante via `next_step_code`. Les codes doivent être en snake_case, sans accents.

OBJECTIF CHIFFRÉ : viser 8 à 12 steps au total pour un parcours inscription complet (vs 25-30 naïvement), dont au plus 3 à 5 interactions utilisateur actives (welcome auto, consent 1 clic, 1 form identité, 1 form contact + OTP, 2-3 uploads, 1 confirm).

**RÈGLE DE STYLE : AUCUN EMOJI.** Jamais d'emoji dans les textes générés : ni dans `question`, ni dans les valeurs de `messages`, ni dans les labels. Pas de 👋, 📋, ✅, 🎉, ⚠️, ✨, 🔍 ni d'autres. Un chatbot professionnel pour une mutuelle d'épargne et de crédit s'exprime sobrement en texte simple. Les séparateurs visuels se font avec des sauts de ligne et de la ponctuation (« : », « — »), pas avec des pictogrammes.

Produis maintenant le JSON pour le document ci-dessous.
"""


def _slugify_code(value: str) -> str:
    s = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "step"


def _ensure_unique_codes(doc_dict: Dict[str, Any]) -> None:
    seen: Dict[str, int] = {}
    for step in doc_dict.get("steps", []):
        raw = str(step.get("code") or step.get("label") or "step")
        code = _slugify_code(raw)
        if code in seen:
            seen[code] += 1
            code = f"{code}_{seen[code]}"
        else:
            seen[code] = 1
        step["code"] = code


def _normalize_form_types(doc_dict: Dict[str, Any]) -> None:
    """Si le LLM a émis type='form', on le ramène à 'question' (le type réel
    côté enum DB) tout en conservant les form_fields. Le moteur détecte ensuite
    le mode form via la présence de validation_rules.form_fields."""
    for step in doc_dict.get("steps", []):
        if (step.get("type") or "").lower() == "form":
            step["type"] = "question"


def _rechain_forms_in_order(doc_dict: Dict[str, Any]) -> None:
    """Garantit que les steps « form » (steps ayant `form_fields`) sont joués
    dans l'ordre d'apparition dans le document, et que le step précédant le
    premier form pointe bien vers lui.

    Scénario corrigé : le LLM a mis consent_artci.next_step_code = form_famille
    (le dernier form) au lieu de form_identite (le premier). Résultat : le
    chatbot saute Étape 1 et 2. Ici on détecte la chaîne attendue :
      [step précédant le 1er form].next → form[0] → form[1] → … → form[-1].next
    En respectant ce que le LLM a prévu APRÈS le dernier form.
    """
    steps = doc_dict.get("steps") or []
    form_indices: list[int] = []
    for i, s in enumerate(steps):
        rules = s.get("validation_rules") or {}
        if isinstance(rules.get("form_fields"), list) and rules["form_fields"]:
            form_indices.append(i)

    if len(form_indices) < 2:
        return  # 0 ou 1 form : rien à ré-ordonner

    # Chaîne les forms entre eux dans l'ordre du document
    for n in range(len(form_indices) - 1):
        src = steps[form_indices[n]]
        tgt_code = steps[form_indices[n + 1]].get("code")
        if tgt_code:
            src["next_step_code"] = tgt_code

    # Le step qui pointait vers un form « milieu » ou « fin » doit pointer
    # vers le premier form. On trouve tous les steps NON-form qui pointent
    # vers un form interne/final et on les redirige vers form[0].
    first_form_code = steps[form_indices[0]].get("code")
    allowed_form_entries = {first_form_code}
    inner_form_codes = {
        steps[idx].get("code") for idx in form_indices[1:]
    }
    for i, s in enumerate(steps):
        if i in form_indices:
            continue  # on vient de chaîner les forms entre eux
        nxt = s.get("next_step_code")
        if nxt in inner_form_codes:
            s["next_step_code"] = first_form_code
        for key, target in (s.get("branches") or {}).items():
            if target in inner_form_codes:
                s["branches"][key] = first_form_code


def _rebuild_form_question_texts(
    doc_dict: Dict[str, Any],
    lists: Optional[List[ReferenceList]] = None,
) -> None:
    """Pour chaque step « form » (contenant `form_fields`), on reconstruit le
    texte de la question à partir des labels des champs. Cela garantit que
    ce que l'utilisateur voit à l'écran correspond EXACTEMENT à ce que le
    moteur attend — évite les mismatchs quand le LLM mélange le texte d'un
    form avec les champs d'un autre.

    Si un field a `options_ref` et que `lists` contient le référentiel, on
    affiche inline les choix numérotés : `Civilité (1=Mlle, 2=Mme, 3=M.) : `.
    """
    lists_by_key: Dict[str, ReferenceList] = {
        rl.key: rl for rl in (lists or [])
    }
    steps = doc_dict.get("steps", [])
    # Compte combien de forms il y a, pour numéroter dans l'intro.
    form_indices: Dict[int, int] = {}
    counter = 0
    for i, s in enumerate(steps):
        rules = s.get("validation_rules") or {}
        fields = rules.get("form_fields")
        if isinstance(fields, list) and fields:
            counter += 1
            form_indices[i] = counter

    for i, s in enumerate(steps):
        rules = s.get("validation_rules") or {}
        fields = rules.get("form_fields")
        if not isinstance(fields, list) or not fields:
            continue
        step_num = form_indices.get(i, 1)
        lines = [
            f"Étape {step_num} — copiez le modèle ci-dessous, remplissez-le "
            "et renvoyez-le en UN SEUL message :",
            "",
        ]
        for f in fields:
            label = str(f.get("label") or f.get("key") or "").strip()
            if not label:
                continue
            suffix = " (facultatif)" if f.get("optional") else ""
            opts_ref = f.get("options_ref")
            hint = ""
            if opts_ref and opts_ref in lists_by_key:
                rl = lists_by_key[opts_ref]
                opts = " / ".join(
                    f"{idx+1}={it.get('label','')}"
                    for idx, it in enumerate(rl.items or [])
                )
                if opts:
                    hint = f" ({opts})"
            lines.append(f"{label}{hint}{suffix} : ")
        s["question"] = "\n".join(lines)


def _build_reference_lists_block(lists: List[ReferenceList]) -> str:
    """Construit le bloc à injecter dans le prompt pour informer le LLM des
    référentiels disponibles et de leurs clés techniques."""
    if not lists:
        return ""
    lines = [
        "",
        "RÉFÉRENTIELS FERMÉS DISPONIBLES — si un champ ou une question y correspond, "
        "émets `options_ref: \"<key>\"` au lieu d'un regex. Clés disponibles :",
        "",
    ]
    for rl in lists:
        values = ", ".join(it.get("label", "") for it in (rl.items or [])[:8])
        aliases = ", ".join(rl.aliases or [])
        line = f"- `{rl.key}` — {rl.label} (ex. : {values})"
        if aliases:
            line += f" [déclencheurs : {aliases}]"
        lines.append(line)
    return "\n".join(lines)


def _attach_options_refs(
    doc_dict: Dict[str, Any],
    lists: List[ReferenceList],
) -> None:
    """Post-processeur de sécurité : si un field (ou step) n'a pas d'`options_ref`
    mais que son label correspond à une liste connue, l'attache automatiquement
    et retire tout regex incompatible."""
    if not lists:
        return
    for step in doc_dict.get("steps", []):
        rules = step.get("validation_rules") or {}
        # Au niveau step (hors form)
        if not rules.get("options_ref"):
            matched = reference_list_service.match_list_for_label(
                lists, step.get("label", "") or step.get("code", "")
            )
            # On n'attache au niveau step que si le step n'a pas de form_fields
            if matched and not rules.get("form_fields"):
                rules["options_ref"] = matched
                rules.pop("regex", None)
                step["validation_rules"] = rules
        # Au niveau de chaque form_field
        fields = rules.get("form_fields")
        if isinstance(fields, list):
            for f in fields:
                if f.get("options_ref"):
                    continue
                matched = reference_list_service.match_list_for_label(
                    lists, str(f.get("label") or f.get("key") or "")
                )
                if matched:
                    f["options_ref"] = matched
                    f.pop("regex", None)
                    f.pop("format", None)
            step["validation_rules"] = rules


def _inject_update_gates(doc_dict: Dict[str, Any]) -> None:
    """Pour les parcours de mise à jour, injecte automatiquement
    `meta.show_when` sur les steps de domaine pour qu'ils soient skippés
    quand leur domaine n'a pas été coché dans le multi-select
    `choix_modification`. Le LLM oublie souvent cette règle, on compense ici.
    """
    meta = doc_dict.get("meta") or {}
    name = (meta.get("name") or "").lower()
    description = (meta.get("description") or "").lower()
    is_update = any(
        kw in (name + " " + description)
        for kw in [
            "mise à jour", "mise a jour", "modifi", "modifier", "modification",
            "actualis", "changer", "update",
        ]
    )
    steps = doc_dict.get("steps") or []
    # Cherche aussi si un step a multi_select — c'est signe d'un parcours update
    has_multi = any(
        isinstance(s, dict)
        and (s.get("validation_rules") or {}).get("multi_select")
        for s in steps
    )
    if not (is_update or has_multi):
        return

    # Trouve le step de choix (multi_select)
    choix_step = next(
        (s for s in steps if isinstance(s, dict) and (s.get("validation_rules") or {}).get("multi_select")),
        None,
    )
    # Fallback : si pas de multi_select mais un step nommé « choix_modification »
    # ou similaire, on l'injecte automatiquement comme multi_select.
    if choix_step is None and is_update:
        for s in steps:
            if not isinstance(s, dict):
                continue
            code = (s.get("code") or "").lower()
            label = (s.get("label") or "").lower()
            if any(kw in (code + " " + label) for kw in [
                "choix_modif", "choix modif", "domaine", "que souhait", "souhaitez",
                "a modifier", "à modifier",
            ]):
                rules = dict(s.get("validation_rules") or {})
                rules["multi_select"] = [
                    {"code": "coordonnees", "label": "Coordonnées"},
                    {"code": "employeur",   "label": "Employeur"},
                    {"code": "situation",   "label": "Situation matrimoniale"},
                    {"code": "piece",       "label": "Pièce d'identité"},
                ]
                rules["min_selected"] = 1
                s["validation_rules"] = rules
                # Vire une éventuelle options_ref qui bloquerait la détection
                rules.pop("options_ref", None)
                s["type"] = "question"
                choix_step = s
                log.info("Parcours update : multi_select auto-injecté sur '%s'", s.get("code"))
                break
    if choix_step is None:
        return
    choix_code = choix_step.get("code") or "choix_modification"
    gate_key = f"{choix_code}_items"

    # Patterns → code de domaine
    DOMAINS = [
        ("coordonnees", ["coordon", "contact", "telephone", "téléphone", "email",
                         "mail", "domicile", "adresse", "postale", "postal"]),
        ("employeur", ["employeur", "societe", "société", "matricule", "categorie",
                       "catégorie", "direction", "service", "exploitation"]),
        ("situation", ["situation", "matrimonial", "conjoint"]),
        ("piece", ["piece_identite", "pièce", "piece", "cni", "passeport",
                   "recto", "verso", "signature"]),
    ]

    def _match_domain(step: dict) -> Optional[str]:
        code = (step.get("code") or "").lower()
        label = (step.get("label") or "").lower()
        rules = step.get("validation_rules") or {}
        fields = rules.get("form_fields") or []
        field_text = " ".join(
            str(f.get("key", "")).lower() + " " + str(f.get("label", "")).lower()
            for f in fields
        )
        haystack = f"{code} {label} {field_text}"
        for domain_code, patterns in DOMAINS:
            for pat in patterns:
                if pat in haystack:
                    return domain_code
        return None

    # Après choix_step, injecte show_when sur chaque step de domaine
    seen_choix = False
    injected = 0
    for s in steps:
        if not isinstance(s, dict):
            continue
        if s is choix_step:
            seen_choix = True
            continue
        if not seen_choix:
            continue
        if s.get("type") not in ("question", "message"):
            continue
        code = (s.get("code") or "").lower()
        # Skip les steps système (build_recap, confirm, save_dossier, completion)
        if any(sys in code for sys in ("build_recap", "confirm", "save_dossier", "completion", "recap")):
            continue
        meta_s = dict(s.get("meta") or {})
        if "show_when" in meta_s:
            continue  # déjà posé
        domain = _match_domain(s)
        if not domain:
            continue
        meta_s["show_when"] = {"key": gate_key, "in": domain}
        s["meta"] = meta_s
        injected += 1
    if injected:
        log.info("Parcours de mise à jour : %d show_when injectés automatiquement", injected)

    # Dans un parcours de mise à jour, TOUS les champs de form_fields deviennent
    # optionnels — l'utilisateur ne modifie que ce qu'il veut, pas tout à la fois.
    # On met aussi required=false pour la compat front.
    opt_count = 0
    for s in steps:
        if not isinstance(s, dict):
            continue
        rules = s.get("validation_rules") or {}
        form_fields = rules.get("form_fields")
        if not form_fields:
            continue
        # Ignore les forms qui n'ont pas de show_when (= pas un form de domaine)
        if not (s.get("meta") or {}).get("show_when"):
            continue
        for f in form_fields:
            f["optional"] = True
            f["required"] = False
            opt_count += 1
    if opt_count:
        log.info("Parcours de mise à jour : %d champs passés en optionnel", opt_count)


def _ensure_save_dossier_step(doc_dict: Dict[str, Any]) -> None:
    """Filet de sécurité : si le LLM a oublié d'insérer `save_dossier`, on
    l'ajoute entre `confirm` et `completion` pour garantir la création du
    dossier en base et la génération du numéro sociétaire.
    """
    steps = doc_dict.get("steps") or []
    if not isinstance(steps, list) or not steps:
        return

    already = any(
        (s.get("action_name") or "").strip() == "create_real_dossier"
        for s in steps
        if isinstance(s, dict)
    )
    if already:
        return

    # Cherche l'index du step confirm (type=question code=confirm) et du
    # completion (type=message code=completion). On insère entre les deux.
    def _find_index(predicate) -> int:
        for i, s in enumerate(steps):
            if isinstance(s, dict) and predicate(s):
                return i
        return -1

    i_confirm = _find_index(
        lambda s: s.get("code") == "confirm" or (s.get("type") == "question" and "confirm" in (s.get("code") or ""))
    )
    i_completion = _find_index(
        lambda s: s.get("code") == "completion" or s.get("template_code") == "ma2e.completion"
    )

    insert_at = i_completion if i_completion >= 0 else len(steps)
    if i_confirm >= 0 and (i_completion < 0 or i_confirm < i_completion):
        insert_at = i_confirm + 1

    save_step = {
        "order": 0,
        "code": "save_dossier",
        "label": "Enregistrement du dossier",
        "description": "Enregistre votre dossier dans le système et génère votre numéro sociétaire.",
        "type": "action",
        "question": None,
        "template_code": None,
        "action_name": "create_real_dossier",
        "next_step_code": (steps[i_completion].get("code") if i_completion >= 0 else None),
        "branches": {},
        "validation_rules": {},
    }
    # Rebranche le confirm sur save_dossier
    if i_confirm >= 0:
        confirm_step = steps[i_confirm]
        if isinstance(confirm_step, dict):
            branches = dict(confirm_step.get("branches") or {})
            # branches "yes"/"non" ou simplement next_step_code
            if confirm_step.get("next_step_code") == (steps[i_completion].get("code") if i_completion >= 0 else None):
                confirm_step["next_step_code"] = "save_dossier"
            for k, v in list(branches.items()):
                if i_completion >= 0 and v == steps[i_completion].get("code"):
                    branches[k] = "save_dossier"
            if branches:
                confirm_step["branches"] = branches
    steps.insert(insert_at, save_step)
    # Renumérote les orders pour rester cohérent.
    for i, s in enumerate(steps, start=1):
        if isinstance(s, dict):
            s["order"] = i
    log.info("LLM parcours : étape save_dossier auto-injectée à l'index %d", insert_at)


async def extract_parcours_from_text(
    text: str,
    filename: str = "",
    db: Optional[AsyncSession] = None,
    tenant_id=None,
) -> ParcoursDocument:
    """Appelle le LLM et renvoie un ParcoursDocument validé.

    Si `db` et `tenant_id` sont fournis, injecte dans le prompt la liste des
    référentiels fermés disponibles ET passe un post-processeur fuzzy qui
    attache automatiquement les `options_ref` manquants.

    Lève `ValueError` si la sortie LLM est incohérente.
    """
    text = (text or "").strip()
    if len(text) < 20:
        raise ValueError(
            "Le document est vide ou trop court. Rédigez le titre et la liste des questions."
        )
    if len(text) > 20_000:
        text = text[:20_000] + "\n\n[...tronqué...]"

    # Charge les référentiels pour l'injection prompt + post-processing.
    reference_lists: List[ReferenceList] = []
    if db is not None and tenant_id is not None:
        try:
            await reference_list_service.seed_system_lists(db, tenant_id)
            reference_lists = await reference_list_service.list_lists(db, tenant_id)
        except Exception as e:  # pragma: no cover
            log.warning("Chargement référentiels pour LLM échoué : %s", e)
            reference_lists = []

    system_prompt = SYSTEM_PROMPT + _build_reference_lists_block(reference_lists)

    user_message = f"Document source ({filename or 'sans nom'}) :\n\n{text}"
    try:
        payload: Dict[str, Any] = await llm_azure.structured_output(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=12000,
        )
    except RuntimeError as exc:
        log.warning("LLM parcours : appel Azure échoué (%s)", exc)
        raise ValueError(
            f"Appel au modèle IA impossible : {exc}. Vérifiez la configuration Azure OpenAI."
        ) from exc

    if not payload or not isinstance(payload, dict):
        raise ValueError(
            "Le modèle n'a rien renvoyé d'exploitable. Simplifiez votre document "
            "(titre + liste numérotée des questions) et réessayez."
        )
    if not payload.get("steps"):
        log.warning("LLM parcours : payload sans steps. Payload=%s", str(payload)[:400])
        raise ValueError(
            "Le modèle n'a pas identifié de questions dans votre document. "
            "Assurez-vous que les questions sont bien numérotées (1. Nom, 2. Prénoms, …)."
        )

    _normalize_form_types(payload)
    _ensure_unique_codes(payload)
    _rechain_forms_in_order(payload)
    _attach_options_refs(payload, reference_lists)
    _rebuild_form_question_texts(payload, reference_lists)
    _ensure_save_dossier_step(payload)
    _inject_update_gates(payload)

    try:
        doc = document_from_dict(payload)
    except ValueError as exc:
        log.warning("LLM parcours : schéma invalide (%s). Payload=%s", exc, str(payload)[:400])
        raise ValueError(f"Parcours extrait invalide :\n{exc}") from exc
    return doc
