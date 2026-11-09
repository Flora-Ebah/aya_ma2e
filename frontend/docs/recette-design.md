# Recette visuelle du design system — frontend MA2E

Recette réalisée dans le navigateur intégré sur http://localhost:3001 (API http://localhost:8000), comptes de démonstration du README (`admin@ma2e.ci`, `agent@ma2e.ci`). Mesures par script (`window.innerWidth` contrôlé à chaque passe) : défilement horizontal, polices calculées, icônes du sprite, textes coupés, égalité des hauteurs de cartes, cartes orphelines, tableaux qui débordent. Passes faites en clair et en sombre à 1440 px, à 1920 px (dossiers, détail, reporting, QR) et à 390 px (toutes les pages).

Statuts : **OK** (rien à corriger), **corrigé** (défaut trouvé et réparé), **signalé** (limite hors périmètre front).

## Retours utilisateur traités en priorité

| Point | Statut | Détail |
|---|---|---|
| Colonne latérale du détail d'un dossier | corrigé | Le sommaire n'avait aucune plage de collage (l'`aside` s'arrêtait à la hauteur de son contenu : `items-start`) : il défilait avec la page. Ajout de `self-stretch` sur l'`aside` ; le bloc interne reste `position: sticky` (top = header + 16 px), sans `overflow`, sans scroll interne, hauteur 536 px (tient dès 640 px de hauteur de fenêtre). Vérifié à 1440 et 1920 px : top = 72 px après défilement. Sous 1024 px, un sommaire compact en puces (`lg:hidden`) s'affiche au-dessus du contenu (la mise en page passe en colonne). |
| Polices Sora / Outfit / JetBrains Mono | corrigé | Cause racine : `--font-heading/-body/-mono` de `app/tokens.css` pointaient vers `"Sora"`, `"Outfit"`, `"JetBrains Mono"` (noms non installés) au lieu des variables `next/font` : les H1–H4 et valeurs KPI retombaient sur la police système. Les trois variables préfixent maintenant `var(--font-sora)`, `var(--font-outfit)`, `var(--font-jetbrains-mono)`. Ajouts dans `globals.css` : `h1–h4` en Sora, `dialog/table/option/svg text` en `inherit`, titres de cartes H5 (`.sa-card__title--sm`, `.sa-h5`) en Sora. Contrôle par `getComputedStyle` sur toutes les pages : aucune balise de texte hors Outfit/Sora/JetBrains Mono ; H1–H4 et KPI en Sora ; numéros de dossier en mono ; `next/font` chargé aussi sur les pages publiques et le chat (même `layout.tsx` racine). |
| Cartes de statistiques (modèle `sa-kpi` du POC) | corrigé | `KpiCard` (kit) rendait déjà la tuile 40×40 ; ajout des variantes `neutre | marque | ok | warn | error | info` (+ `brand`/`accent`), du mode cliquable (`onClick`, `active` → bouton `aria-pressed`) et des classes CSS `sa-icon-tile--info/--neutre`, `button.sa-kpi`, `.sa-kpi--active`. Remplacement des cartes faites à la main par `KpiCard` dans : liste des dossiers (`_StatsHeader`, 3 par ligne, clic = filtre), reporting (`_KpiSection`, grille `stats3`), sécurité (rétention), connaissances, import de référentiel (résultat). Les pages « accueil » admin / conformité / assistante / référentiels sont des redirections : aucune carte à convertir. |

## Défauts connus de la consigne

| Point | Statut | Détail |
|---|---|---|
| Recherche du header → `/dossiers?q=` | corrigé | La page dossiers lit `q` (`useSearchParams`, enveloppée dans `Suspense`) et pré-remplit/met à jour le champ de recherche. |
| Menu des notifications | signalé | Menu compact (5 entrées max + lien « Voir tous les dossiers ») alimenté par les statistiques de dossiers existantes ; il n'existe ni API de notifications ni page dédiée (« Voir toutes » renvoie vers les dossiers). À faire côté backend. |
| `tokens.css` sombre (`prefers-color-scheme`) | corrigé | Bloc aligné sur les couleurs MA2E (vert #00A045 / orange #FFA500, texte d'accent, focus, graphique). |
| Composants faits à la main | OK | Aucune modale/tiroir maison restant : tout passe par `Modal`/`Drawer` du kit. |
| `components/ui/cx.ts` et `cx.tsx` | corrigé | Aucun import ne passait par eux : supprimés. |
| `npm run lint` | signalé | Pas de config ESLint (non créée). `npx tsc --noEmit` : 0 erreur. |

## Tableau écran → statut

| Écran | Statut | Remarques |
|---|---|---|
| `/login` | OK | Ne défile pas (hauteur document = fenêtre) à 1440 et 390 px, thème clair/sombre/système, validation native. |
| `/dossiers` | corrigé | Cartes KPI avec tuile + filtre au clic ; recherche `?q=` ; tableau en cartes empilées sous 768 px (débordement de 504 px → 390 px). |
| `/dossiers/[id]` | corrigé | Sommaire collant réparé + version compacte sous 1024 px. Dossier de démonstration au statut rejeté : aucune action possible, donc modales de validation/rejet/complément non exercées. |
| `/reporting` | corrigé | Cartes KPI via `KpiCard` (3 par ligne, 8 = 3+3+2), tableau chronologique compact. |
| `/qr-code` | OK | |
| `/administration/utilisateurs` | OK | Création d'un utilisateur testée de bout en bout (validation native, modale sans barre de défilement, Échap, toast, ligne ajoutée, menu ⋯). |
| `/administration/roles` | corrigé | Matrices de permissions : débordement horizontal à 390 px (514 px de large) corrigé. |
| `/administration/securite` | corrigé | Cartes de rétention via `KpiCard`. |
| `/administration/integrations` | OK | |
| `/assistante/personnalite` | OK | |
| `/assistante/parcours` | OK | |
| `/assistante/parcours/[id]` | corrigé | Tiroir d'édition d'étape OK (Échap). Simulateur plein écran : la zone de conversation ne remplissait pas la hauteur, corrigé (`min-height` de `.ass-sim`). |
| `/assistante/emails` | OK | |
| `/assistante/connaissances` | corrigé | Cartes de stats via `KpiCard`. L'ingestion réelle (flux SSE) n'a pas été lancée (appel à un service externe). |
| `/assistante/integrations` | OK | |
| `/conformite/audit` | OK | `/conformite` redirige ici. |
| `/conformite/conversations` | OK | |
| `/referentiels/employeurs` | corrigé | Tableau compact, plus de défilement horizontal à 390 px. |
| `/referentiels/collaborateurs` | OK | |
| `/referentiels/import` | corrigé | Import testé avec un CSV généré (2 lignes valides) ; résultats en `KpiCard`. |
| `/parametres/general`, `/mfa`, `/profil` | OK | |
| `/acces`, `/artci`, `/chat` | OK | `/` redirige vers `/dossiers` quand on est connecté. |
| Shell : sidebar, header, menu utilisateur (clair/sombre/système), notifications | OK | Navigation filtrée par rôle vérifiée avec `agent@ma2e.ci` (dossiers, reporting, QR, paramètres uniquement) ; barre mobile OK à 390 px. |

## Limites de la recette

- Captures d'écran parfois tronquées ou en échec par le volet : la plupart des contrôles sont des mesures par script.
- Non exercés : actions de validation/rejet d'un dossier (aucun dossier actif), pagination et tris avec plus d'une page de données, ingestion réelle, exports.
- Données de test créées en base locale : utilisateur `recette.test@ma2e.ci` et employeurs `RECTEST`, `REC2` — à supprimer si besoin.
- Les boutons de groupe de la sidebar hors-champ (menu mobile fermé) n'ont pas de nom accessible tant que le panneau est fermé : sans effet, le panneau est masqué.
