"""Genere MA2E_Plan_de_Tests_v1.docx
Style naturel, N&B Times New Roman.
"""
from datetime import date
from pathlib import Path

from docx import Document

from _docx_helpers import (
    BUL, CENTER, H, IMG, KVTABLE, NUM, P, PAGE_BREAK, TABLE,
    set_doc_defaults,
)

HERE = Path(__file__).parent
OUT = HERE / "MA2E_Plan_de_Tests_v1.docx"

doc = Document()
set_doc_defaults(doc)

# ============================================================== #
# PAGE DE GARDE
# ============================================================== #
CENTER(doc, "\n\n\n")
CENTER(doc, "MUTUELLE DES AGENTS DE L'EAU ET DE L'ELECTRICITE",
       size=12, bold=True)
CENTER(doc, "Groupe ERANOVE", size=12, italic=True)
CENTER(doc, "\n\n")
CENTER(doc, "MA2E", size=48, bold=True)
CENTER(doc, "\n")
CENTER(doc, "PLAN DE TESTS", size=22, bold=True)
CENTER(doc, "Approche, scénarios, recette métier et critères d'acceptation",
       size=14, italic=True)
CENTER(doc, "\n\n\n\n\n\n")

KVTABLE(doc, [
    ("Référence", "MA2E_Plan_de_Tests_v1.docx"),
    ("Version", "1.0"),
    ("Date", date.today().strftime("%d/%m/%Y")),
    ("Rédigé par", "A. Siriki OUATTARA"),
    ("Validation", "Chef de service MA2E"),
    ("Statut", "Document de travail interne"),
    ("Confidentialité", "Usage interne GS2E / ERANOVE"),
])

PAGE_BREAK(doc)

# ============================================================== #
# SOMMAIRE
# ============================================================== #
H(doc, "Sommaire", level=1)
for i, t in enumerate([
    "Objectifs et périmètre du plan de tests",
    "Approche retenue",
    "Niveaux de tests",
    "Tests techniques automatisés",
    "Tests des parcours utilisateur",
    "Tests de performance",
    "Tests de sécurité",
    "Recette métier (UAT)",
    "Critères de mise en production",
    "Gestion des anomalies",
], 1):
    P(doc, f"{i}. {t}", size=12)

PAGE_BREAK(doc)

# ============================================================== #
# 1. OBJECTIFS
# ============================================================== #
H(doc, "1. Objectifs et périmètre du plan de tests", level=1)
P(doc,
  "Ce plan de tests a un objectif simple : s'assurer que la plateforme MA2E "
  "fonctionne comme attendu, dans tous les cas prévus comme dans les cas "
  "inhabituels, avant chaque mise en production. Il couvre l'ensemble des "
  "fonctionnalités définies dans le backlog (29 user stories réparties sur "
  "9 modules), ainsi que les exigences transverses de sécurité, de "
  "performance et de conformité ARTCI.")

H(doc, "1.1 Ce qui est testé", level=2)
BUL(doc, "Les parcours sociétaire sur WhatsApp et sur le chat web (enrôlement complet, questions à AYA, escalade vers un conseiller).")
BUL(doc, "Le back-office des agents MA2E (connexion, traitement des dossiers, exports, audit).")
BUL(doc, "Les interactions avec les services externes (WhatsApp Cloud API, extraction de la CNI, email).")
BUL(doc, "Le respect des règles métier inscrites dans le backlog (durée de session, plafonds de tentatives, conservation des données).")
BUL(doc, "La conformité avec la loi 2013-450 (consentement, droit à l'oubli, journal d'audit).")

H(doc, "1.2 Ce qui n'est pas testé", level=2)
BUL(doc, "L'infrastructure Azure elle-même (couverte par l'engagement de service de Microsoft).")
BUL(doc, "L'audit de sécurité externe certifié ARTCI, qui fera l'objet d'une intervention indépendante en V2.")
BUL(doc, "Les cas d'usage hors ligne : la plateforme nécessite une connexion Internet.")

PAGE_BREAK(doc)

# ============================================================== #
# 2. APPROCHE
# ============================================================== #
H(doc, "2. Approche retenue", level=1)
P(doc,
  "L'approche est volontairement industrielle : le maximum de tests est "
  "automatisé pour permettre une exécution rapide à chaque modification, et "
  "le minimum est laissé en manuel pour ne mobiliser la cellule MA2E que sur "
  "ce qui apporte réellement de la valeur (les parcours utilisateur du "
  "monde réel).")

H(doc, "2.1 Principes", level=2)
BUL(doc, "Tout test qui peut être automatisé l'est. Les tests manuels sont réservés aux situations qui demandent un jugement humain.")
BUL(doc, "Les jeux de données utilisés en recette sont anonymisés. Aucune donnée réelle d'un sociétaire n'est utilisée hors production.")
BUL(doc, "La chaîne de mise en production bloque automatiquement le passage en recette si un seul test automatisé échoue.")
BUL(doc, "Les services externes critiques (WhatsApp, extraction de la CNI) sont sollicités réellement en environnement de recette, pour vérifier les intégrations dans des conditions réalistes.")

PAGE_BREAK(doc)

# ============================================================== #
# 3. NIVEAUX
# ============================================================== #
H(doc, "3. Niveaux de tests", level=1)
P(doc,
  "Les tests sont organisés en cinq niveaux, du plus rapide et le plus "
  "automatisé au plus proche de l'expérience utilisateur réelle. Le schéma "
  "ci-dessous présente la répartition habituellement retenue dans ce type de "
  "projet.")

IMG(doc, HERE / "diagram_pyramide_tests.png", width_cm=14,
    caption="Schéma 1 — Pyramide de tests retenue pour MA2E")

TABLE(doc,
    ["Niveau", "Volume cible", "Durée d'exécution", "Quand sont-ils joués ?"],
    [
        ("Tests unitaires", "Environ 450 tests", "Moins de 30 secondes", "À chaque modification du code"),
        ("Tests d'intégration", "Environ 80 tests", "Moins de 3 minutes", "À chaque proposition de modification"),
        ("Tests end-to-end", "Environ 15 parcours", "Moins de 8 minutes", "Avant tout passage en recette ou production"),
        ("Tests de performance", "5 scénarios", "30 minutes", "Toutes les semaines"),
        ("Recette métier (UAT)", "Environ 25 cas", "1 journée", "Avant chaque mise en production majeure"),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 4. TESTS TECHNIQUES
# ============================================================== #
H(doc, "4. Tests techniques automatisés", level=1)
H(doc, "4.1 Tests unitaires", level=2)
P(doc,
  "Les tests unitaires vérifient le bon fonctionnement de chaque morceau de "
  "code pris isolément. Ils sont les plus nombreux, les plus rapides à "
  "exécuter, et constituent le filet de sécurité de l'équipe technique au "
  "quotidien.")

TABLE(doc,
    ["Module concerné", "Exemples de cas testés"],
    [
        ("Conversation",
         "Le parcours passe à l'étape suivante quand la réponse est conforme, refuse les transitions interdites, reprend correctement une conversation après pause."),
        ("Extraction des pièces",
         "Réagit correctement à un score élevé, à un score faible, à un format non reconnu, à une erreur du service distant."),
        ("Consentement ARTCI",
         "Signe correctement chaque consentement et vérifie qu'un consentement n'a pas été modifié après coup."),
        ("Audit",
         "Détecte toute tentative de modification du journal et refuse l'ajout d'une entrée mal formée."),
        ("Validation",
         "Refuse l'attribution d'un numéro de sociétaire si le dossier est incomplet, trace correctement chaque décision."),
        ("Authentification",
         "Refuse une connexion avec un mauvais mot de passe, bloque le compte au-delà de 5 tentatives, vérifie l'expiration de session."),
    ]
)

H(doc, "4.2 Tests d'intégration", level=2)
P(doc,
  "Les tests d'intégration vérifient que plusieurs morceaux de code "
  "fonctionnent correctement ensemble, en interaction avec une base de "
  "données et des services externes simulés. Quelques exemples :")

TABLE(doc,
    ["Cas testé", "Résultat attendu"],
    [
        ("Réception d'un message WhatsApp avec une signature correcte",
         "Le message est enregistré et la conversation progresse à l'étape suivante."),
        ("Réception d'un message avec une signature falsifiée",
         "Le message est rejeté et l'incident est tracé dans l'audit."),
        ("Réception du même message deux fois (double notification Meta)",
         "Le second message est ignoré, sans création de doublon."),
        ("Connexion d'un agent avec ses identifiants Active Directory",
         "L'agent accède au back-office, son profil est créé si c'est sa première connexion."),
        ("Agent A tente d'accéder à un dossier de la société B",
         "L'accès est refusé, l'incident est tracé dans l'audit."),
        ("Validation d'un dossier",
         "Le dossier passe au statut Validé, un numéro de sociétaire est attribué, une notification est émise."),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 5. PARCOURS UTILISATEUR
# ============================================================== #
H(doc, "5. Tests des parcours utilisateur", level=1)
P(doc,
  "Les tests end-to-end rejouent intégralement un parcours utilisateur, dans "
  "un navigateur réel et en interaction avec les services externes "
  "d'environnement de recette. Ils sont la garantie que ce que voit "
  "l'utilisateur correspond bien à ce qui est attendu.")

TABLE(doc,
    ["Identifiant", "Parcours testé", "Critère de succès"],
    [
        ("UI-01",
         "Un sociétaire s'enrôle de bout en bout sur WhatsApp avec une CNI lisible.",
         "Le dossier apparaît en attente de validation dans le back-office en moins de 10 minutes."),
        ("UI-02",
         "Un sociétaire envoie une photo floue.",
         "AYA demande une nouvelle photo en expliquant le défaut, jusqu'à trois tentatives."),
        ("UI-03",
         "Un sociétaire pose 10 questions courantes à AYA (avantages, pièces, délais...).",
         "Au moins 8 réponses sont jugées correctes par la cellule MA2E."),
        ("UI-04",
         "Un agent traite 20 dossiers consécutifs en back-office (validation, refus, complément).",
         "Aucune erreur affichée, temps moyen de traitement inférieur à 90 secondes par dossier."),
        ("UI-05",
         "Un superviseur exporte la liste mensuelle des sociétaires validés.",
         "Le fichier obtenu est conforme au gabarit attendu par le service paie."),
        ("UI-06",
         "Un sociétaire interrompt son parcours et y revient le lendemain.",
         "AYA reprend la conversation à l'étape exacte où le sociétaire s'était arrêté."),
        ("UI-07",
         "Un sociétaire demande à parler à un conseiller humain.",
         "La conversation est versée dans la file d'attente, l'agent reçoit l'historique complet."),
        ("UI-08",
         "Un sociétaire refuse le consentement ARTCI.",
         "Le parcours s'arrête, aucune donnée personnelle n'est conservée."),
        ("UI-09",
         "L'agent demande un complément, le sociétaire répond après 14 jours.",
         "Le dossier reprend correctement, le délai n'est pas expiré."),
        ("UI-10",
         "Le DPO traite une demande de droit à l'oubli.",
         "Le dossier est anonymisé, un accusé daté est produit."),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 6. PERFORMANCE
# ============================================================== #
H(doc, "6. Tests de performance", level=1)
P(doc,
  "Les tests de performance simulent une activité soutenue pour vérifier "
  "que la plateforme tient la charge sans dégradation. Ils sont exécutés une "
  "fois par semaine en environnement de recette, sur des plages horaires "
  "creuses.")

TABLE(doc,
    ["Scénario", "Charge simulée", "Critère de succès"],
    [
        ("Réception de messages WhatsApp",
         "200 messages par seconde pendant 10 minutes",
         "Aucun message perdu, temps de traitement inférieur à 200 ms dans 95 % des cas."),
        ("Consultation des dossiers en back-office",
         "50 agents simultanés",
         "Temps de chargement inférieur à 2 secondes."),
        ("Téléversement de photos de CNI",
         "20 téléversements par minute pendant 10 minutes",
         "Aucun échec, temps de téléversement inférieur à 1 seconde."),
        ("Questions à AYA",
         "30 questions simultanées",
         "Temps de réponse moyen inférieur à 3 secondes."),
        ("Journée type",
         "Mélange réaliste sur 24 heures",
         "Aucune dégradation visible, ressources sous 70 % d'occupation."),
    ]
)

H(doc, "6.1 Ce qui est observé pendant les tests", level=2)
BUL(doc, "Le temps de réponse moyen et le temps de réponse dans les 95 % des cas les plus rapides.")
BUL(doc, "Le taux d'erreur (cible : moins de 0,1 % de requêtes en erreur).")
BUL(doc, "La consommation des ressources (mémoire, processeur) des composants applicatifs.")
BUL(doc, "Le nombre de connexions actives à la base de données.")

PAGE_BREAK(doc)

# ============================================================== #
# 7. SECURITE
# ============================================================== #
H(doc, "7. Tests de sécurité", level=1)
P(doc,
  "La sécurité est vérifiée à deux niveaux : par une analyse du code source "
  "(détection automatique des défauts connus) et par une analyse en "
  "fonctionnement réel (tentatives d'attaques courantes).")

H(doc, "7.1 Analyse du code", level=2)
BUL(doc, "Vérification automatique de l'absence de mots de passe ou de clés inscrits en clair dans le code.")
BUL(doc, "Détection des vulnérabilités connues dans les bibliothèques utilisées (mises à jour régulières).")
BUL(doc, "Contrôle de qualité du code (cohérence, gestion correcte des erreurs, absence d'accès non autorisés).")

H(doc, "7.2 Analyse en fonctionnement", level=2)
P(doc,
  "Avant chaque mise en production, une analyse dynamique simule les "
  "tentatives d'attaques les plus courantes :")

TABLE(doc,
    ["Type d'attaque simulé", "Résultat attendu"],
    [
        ("Injection dans les champs de saisie",
         "Tous les champs sont nettoyés, aucune requête modifiée ne passe."),
        ("Tentative d'accès à un dossier d'une autre société",
         "Accès systématiquement refusé."),
        ("Tentative de connexion par force brute",
         "Le compte est bloqué temporairement après 5 tentatives."),
        ("Falsification du jeton de session",
         "La session est rejetée, l'utilisateur est redirigé vers la page de connexion."),
        ("Tentative de manipulation du consentement ARTCI",
         "La modification est détectée par la signature, le consentement est rejeté."),
        ("Réémission d'un message WhatsApp falsifié",
         "Le message est rejeté, l'incident est tracé."),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 8. UAT
# ============================================================== #
H(doc, "8. Recette métier (UAT)", level=1)
P(doc,
  "La recette métier est pilotée par la cellule MA2E. Elle se déroule sur "
  "une journée par version majeure, en environnement de recette, avec des "
  "données anonymisées représentatives. L'objectif est de confirmer que la "
  "plateforme rend bien le service attendu, du point de vue de ses futurs "
  "utilisateurs.")

TABLE(doc,
    ["Identifiant", "Cas de recette", "Réalisé par", "Critère de succès"],
    [
        ("UAT-01",
         "Enrôlement complet d'un sociétaire fictif via WhatsApp.",
         "Cellule MA2E",
         "Dossier en attente de validation en moins de 10 minutes."),
        ("UAT-02",
         "Enrôlement d'un sociétaire fictif depuis le chat web.",
         "Cellule MA2E",
         "Parcours équivalent à WhatsApp, aucune fonctionnalité manquante."),
        ("UAT-03",
         "Test du parcours avec une photo de CNI floue.",
         "Cellule MA2E",
         "Demande de re-soumission claire, sans confusion."),
        ("UAT-04",
         "Liste de 10 questions courantes posées à AYA.",
         "Cellule MA2E",
         "Au moins 8 réponses jugées pertinentes et correctement formulées."),
        ("UAT-05",
         "Traitement de 20 dossiers de bout en bout par un agent.",
         "Agent MA2E test",
         "Aucune erreur, temps moyen inférieur à 90 secondes par dossier."),
        ("UAT-06",
         "Génération de l'export mensuel des sociétaires validés.",
         "Administrateur MA2E",
         "Fichier conforme au gabarit du service paie."),
        ("UAT-07",
         "Consultation du journal d'audit sur une plage donnée.",
         "DPO MA2E",
         "Toutes les actions attendues sont retracées avec horodatage."),
        ("UAT-08",
         "Traitement d'une demande de droit à l'oubli.",
         "DPO MA2E",
         "Dossier anonymisé, accusé d'exécution produit."),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 9. GO/NO-GO
# ============================================================== #
H(doc, "9. Critères de mise en production", level=1)
P(doc,
  "Le passage en production est conditionné par la levée des critères "
  "suivants. Les critères marqués \"bloquant\" doivent obligatoirement être "
  "satisfaits ; les autres peuvent faire l'objet d'un plan de correction "
  "engagé.")

TABLE(doc,
    ["Critère", "Seuil attendu", "Bloquant"],
    [
        ("Tests techniques automatisés", "100 % verts", "Oui"),
        ("Tests des parcours utilisateur", "100 % verts en recette", "Oui"),
        ("Performance : réception WhatsApp", "Tenue de 200 messages/seconde", "Oui"),
        ("Sécurité : analyse du code", "Aucune vulnérabilité majeure", "Oui"),
        ("Sécurité : tests en fonctionnement", "Aucune attaque simulée réussie", "Oui"),
        ("Recette métier", "90 % des cas validés", "Oui"),
        ("Documentation", "Architecture, procédures et runbooks à jour", "Oui"),
        ("Anomalies critiques ouvertes", "Aucune", "Oui"),
        ("Anomalies majeures ouvertes", "Au plus 3, avec plan de correction", "Non bloquant"),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 10. ANOMALIES
# ============================================================== #
H(doc, "10. Gestion des anomalies", level=1)
P(doc,
  "Toute anomalie détectée pendant les tests ou en production fait l'objet "
  "d'un suivi formel. Le niveau de gravité fixe le délai de correction "
  "attendu.")

TABLE(doc,
    ["Niveau", "Définition", "Délai de correction"],
    [
        ("Critique",
         "Service indisponible, perte de données ou fuite d'information confidentielle.",
         "Moins de 4 heures."),
        ("Majeur",
         "Une fonctionnalité importante ne fonctionne pas et il n'existe pas de contournement.",
         "Moins de 2 jours."),
        ("Mineur",
         "Anomalie sans impact bloquant ou avec un contournement simple.",
         "Lot de correction suivant."),
        ("Cosmétique",
         "Défaut d'affichage ou inconfort visuel sans impact fonctionnel.",
         "À planifier, sans engagement de date."),
    ]
)

H(doc, "10.1 Suivi des anomalies", level=2)
BUL(doc, "Chaque anomalie est ouverte dans l'outil de suivi des équipes techniques.")
BUL(doc, "Une anomalie comporte au minimum : description du contexte, étapes de reproduction, comportement attendu, comportement observé, captures d'écran si pertinent.")
BUL(doc, "Le tri des anomalies est revu hebdomadairement par le responsable technique et la cellule MA2E.")
BUL(doc, "Aucune mise en production ne peut avoir lieu tant qu'il reste une anomalie critique ouverte.")

doc.save(OUT)
print(f"OK  Document genere : {OUT}")
