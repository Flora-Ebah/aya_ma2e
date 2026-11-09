# Kit de composants UI — MA2E (design system GS2E / SARA)

Import unique : `import { Button, Card, DataTable, … } from "@/components/ui";`
Les composants s'appuient sur les classes `.sa-*` (`app/poc-design/sara.css`, `plateforme.css`, `kit.css`) et les tokens GS2E (couleurs de marque MA2E : vert `#00A045`, orange `#FFA500`). Ils gèrent clair/sombre, focus visible, cibles 44 px.

Règles : jamais d'emoji ni d'autre bibliothèque d'icônes (`<Icon name="…" />` uniquement) ; statut/priorité/délai = icône + texte ; une seule action primaire par zone ; un détail est une **page** (pas une modale) ; modale = petit formulaire / confirmation sans barre de défilement ; « Afficher plus » = tiroir plein écran.

## Icônes

`<Icon name="home-01" />` (20 px) · `size={16}` · `label="Valider"` (sinon `aria-hidden`). Props de composants qui acceptent une icône (`icon`, `iconRight`) : nom du sprite (`"plus-sign"`) **ou** élément React.
L'ancien `components/icons.tsx` (IconX, IconCheck…) est supprimé : n'utiliser que `<Icon name="…" />`.

Noms disponibles (sprite `public/design/icons.svg`, HugeIcons Stroke 1.5) :

```
activity-01 add-circle add-team ai-brain-01 ai-chat-02 ai-magic alarm-clock alert-02 alert-circle alert-diamond
analytics-01 archive archive-02 archive-03 arrow-down-01 arrow-down-02 arrow-left-01 arrow-left-02 arrow-right-01
arrow-right-02 arrow-up-01 arrow-up-02 arrow-up-double arrow-up-down arrow-up-right-01 attachment-01 audit-01
bar-chart book-02 book-open-01 bookmark-01 briefcase-01 building-01 building-02 building-03 calendar-01 calendar-03
call call-02 camera-01 cancel-01 cancel-circle chart-decrease chart-histogram chart-increase chart-line-data-01
chart-line-data-02 chat check-list checkmark-badge-01 checkmark-circle-02 checkmark-square-02 clean clipboard
clock-01 clock-02 cloud cloud-loading cloud-saving-done-01 cloud-upload code-square comment-01 computer
computer-desk-01 copy-01 copy-02 customer-service-01 dashboard-circle dashboard-speed-01 dashboard-square-01
database database-01 database-sync delete-01 delete-02 download-02 droplet edit-01 edit-02 exchange-01 eye
file-01 file-download file-export file-import file-upload filter filter-horizontal fingerprint-scan fire flag-01
flash floppy-disk folder-01 folder-open full-screen gas-pipe globe-02 grid-view hand-pointing-right-01 help-circle
help-square hierarchy-square-02 home-01 hourglass id-verified identity-card image-01 image-add-01 inbox
information-circle invoice-01 invoice-03 justice-scale-01 key-01 key-02 keyboard label laptop layers-01 leaf-01
legal-document-01 license link-01 link-square-02 list-view loading-03 location-01 lock-key lock-password login-02
logout-02 magic-wand-01 mail-01 mail-open mail-send-01 mailbox-01 maps-location-01 maximize-screen menu-01
menu-02 message-01 message-notification-01 mic-01 minimize-screen minus-sign money-03 money-not-found-01 moon-01
moon-02 more-horizontal more-vertical navigation-03 note-01 note-edit notification-01 notification-02 paint-board
pause-circle pdf-01 pen-tool-01 percent-circle pie-chart pin pin-02 plant-02 play plug-01 plus-sign printer
qr-code qr-code-01 rain-drop refresh reload robot-01 rocket rotate-01 rotate-left-01 scan search-01 search-02
security-check security-lock sent server-stack-01 settings-01 settings-02 share-01 shield-01 shield-02 shield-key
shield-user sidebar-left signal signal-no-01 signature sink-01 sliders-horizontal smart-phone-01 smart-phone-02
sms-code sorting-01 sparkles square square-lock-02 star star-circle sun-01 sun-03 table tag-01 tag-02 tags tap-01
target-02 task-01 telegram text thumbs-up tick-01 tick-02 tick-double-01 ticket-01 time-01 time-quarter timer-01
tools truck undo unfold-less unfold-more upload-02 user user-add-01 user-block-01 user-check-01 user-circle
user-edit-01 user-group user-multiple user-multiple-02 user-remove-01 user-settings-01 video-01 view view-off
wallet-01 water-energy water-pump webhook whatsapp wifi-01 wifi-02 wifi-disconnected-01 wifi-off-01 wrench-01 zap
```

Ajouter une icône : ajouter `'nom':'NomExportHugeicons'` dans un script du type `build-icons.mjs` (design-system GS2E, paquet `@hugeicons/core-free-icons`) et l'ajouter au sprite ; le sprite est lu au rendu serveur (`IconSprite`), recharger la page.

## Boutons

| Composant | Props principales |
|---|---|
| `Button` | `variant` primary\|secondary\|outline\|ghost\|danger · `size` sm\|md\|lg · `icon`/`iconRight` · `loading` · `block` · tout attribut `<button>` (type="button" par défaut) |
| `ButtonLink` | idem + `href` (next/link) |
| `IconButton` | `icon` (nom) · `label` (obligatoire, aria-label) · `variant` default\|outline\|primary · `dot` · `tooltip` |

Classes : `sa-btn sa-btn--{primary,secondary,outline,ghost,danger,sm,lg,block}`, `sa-icon-btn`. `buttonClass({variant,size})` pour styler un `<Link>`.

```tsx
<Button icon="plus-sign" onClick={ouvrir}>Nouveau dossier</Button>
<Button variant="danger" loading={busy}>Supprimer</Button>
<IconButton icon="cancel-01" label="Fermer" onClick={close} />
```

## Formulaires

`Field` (label, `help`, `error`, `required`, `optional`, `full`) fournit id / `aria-invalid` / `aria-describedby` à ses enfants : `Input` (`mono`, `onValueChange`), `Select`, `Textarea`, `FileInput` (`hint`, `onFiles`), `SearchInput`. `Checkbox` (`label`, `description`, `radio`, `onCheckedChange`), `Switch` (`checked`, `onChange`, `label`), `TextField` (ancienne API tout-en-un conservée).
Mise en page : `FormGrid` (`sa-form-grid` : **3 colonnes ≥ 1280 px**, 2 de 768 à 1279, 1 mobile ; `as="form"` possible), un champ long/seul : `<Field full>` ; `FormActions` (boutons sur une ligne, `sticky`, `align`).

```tsx
<FormGrid as="form" onSubmit={submit}>
  <Field label="Nom" required error={err.nom}><Input value={nom} onValueChange={setNom} /></Field>
  <Field label="Rôle" help="Détermine les accès"><Select value={role} onValueChange={setRole}>…</Select></Field>
  <Field label="Note" full><Textarea value={n} onValueChange={setN} /></Field>
  <FormActions><Button type="submit">Enregistrer</Button><Button variant="secondary">Annuler</Button></FormActions>
</FormGrid>
```

## Cartes, grilles, KPI

- `Card` (`title`, `subtitle`, `actions`, `footer`, `noPadding`, `interactive`, `selected`) · `CardHeader` · `KeyValueList` (`items=[{label,value,icon}]`, `stacked`).
- `ExpandableCard` (props de `Card` + `maxHeight`, `moreLabel`, `drawerTitle`, `drawerContent`, `mode` drawer\|inline) : tronque puis « Afficher plus » → **tiroir plein écran**.
- `Grid` (`variant` : `cards2` 2 par ligne, `stats3` groupes de 3 équilibrés, `kpi` 2 par ligne ; hauteur égale, dernière carte impaire pleine largeur).
- `KpiCard` (`label`, `value`, `unit`, `icon`, `iconTone` brand\|accent\|ok\|warn\|error, `trend={{delta, goodWhenUp}}`, `meta`, `valueTone`, `href`) · `Trend`.

## Badges (icône + texte, `nowrap`)

`Badge` (`tone` neutral\|success\|info\|warning\|danger\|accent\|brand, `icon`, `variant`) · `StatusBadge` (`status` : en_cours, soumis, en_validation, valide, rejete, complement_requis, nouveau, actif, inactif, ok, erreur, en_attente… voir `STATUS_MAP` ; `label`, `tone`, `icon` pour surcharger) · `PriorityBadge` (`priority` p1–p4 ou critique/haute/normale/basse) · `DeadlineBadge` (`due` date ISO **ou** `state` ok\|watch\|risk\|late\|paused\|done-ok\|done-late + `time`) · `deadlineFromDate()`. `StatusPill` = alias déprécié de `StatusBadge`.

## Navigation de contenu

- `Tabs` (`tabs=[{id,label,icon,count,disabled}]`, `value`, `onChange`, `label`) + `TabPanel` (`tabId`, `active`).
- `Chip` / `ChipGroup` (`options`, `value`, `onChange`) / `FilterBar` (filtres **sur une ligne**, `end` à droite).
- `Pagination` (`page`, `total`, `pageSize`, `onPageChange`, `noun`).
- `Accordion` (`items=[{id,title,summary,actions,content,defaultOpen}]`, `single`).

## DataTable

```tsx
<Card noPadding title="Dossiers">
  <FilterBar><SearchInput … /><Select …/></FilterBar>
  <DataTable caption="Liste des dossiers" rows={rows} rowKey={(r) => r.id} loading={loading}
    columns={[
      { key: "ref", header: "N°", mono: true, sortable: true },
      { key: "nom", header: "Agent", sortable: true, accessor: (r) => r.nom },
      { key: "statut", header: "Statut", tight: true, render: (r) => <StatusBadge status={r.statut} /> },
    ]}
    actions={(r) => ({ primary: { label: "Ouvrir", icon: "view", href: `/dossiers/${r.id}` },
                       menu: [{ label: "Supprimer", icon: "delete-02", danger: true, onClick: () => del(r) }] })} />
</Card>
```

Colonnes : `key`, `header`, `render`, `accessor`, `sortable`, `numeric`, `tight`, `mono`, `hideOnMobile`. Options : `pageSize` (25, 0 = sans pagination), pagination serveur (`page`+`total`+`onPageChange`), tri serveur (`sort`+`onSortChange`), `defaultSort`, `onRowClick`, `rowClassName`, `maxHeight` (défilement interne + en-têtes sticky), `empty`, `cards` (repli en cartes < 768 px), `noun`. **≤ 5–6 colonnes**, pas de scroll horizontal. `RowActions` (`primary` + `menu`) utilisable seul. Menus : `DropdownMenu` (`items`, `label`, `icon`) ; `Popover` (déclencheur + panneau en portail, jamais coupé par `overflow`).

## Modale, tiroir, confirmations, toasts

- `Modal` (`open`, `onClose`, `title`, `subtitle`, `icon`, `danger`, `footer`, `size` sm\|md\|lg, `persistent`) : `<dialog>` natif (focus piégé, Échap, pile unique). Petits formulaires uniquement.
- `Drawer` (`open`, `onClose`, `title`, `subtitle`, `actions`, `variant` fullscreen\|side, `footer`) : tiroir plein écran avec bouton **Fermer**.
- `useConfirm()` → `await confirm({ title, message, confirmText, cancelText, variant: "default"|"danger"|"success", icon })` (API inchangée). `useToast()` → `toast({ tone: "success"|"error"|"info"|"warning", title?, message })`.

## En-têtes de page

`PageHeader` (`breadcrumb`, `title`, `description`, `actions`) · `Breadcrumb` (`items=[{label,href?}]`) · `DetailHeader` (`backHref`/`onBack`, `backLabel`, `breadcrumb`, `title`, `badges`, `actions`) · `SectionTitle` (`num`).

## Divers

`EmptyState` (`icon` nom, `title`, `description`, `action`, `compact`) · `Skeleton` / `SkeletonCard` / `SkeletonKpis` · `Spinner` · `Alert` (`tone`, `title`, `actions`, `compact`) · `Avatar` (`name`, `size` 24\|32\|40\|48, `soft`, `status`) · `Tooltip` (`content`, `position`) · `ProgressBar` (`value`, `label`, `tone`, `size`) · `Gauge` (`value`, `max`, `threshold`, `label`, `display`) · `Toolbar` (`left`/`right`).

## Classes `.sa-*` utiles pour du balisage direct

Texte : `sa-h1…sa-h5`, `sa-body`, `sa-body-sm`, `sa-text-soft`, `sa-mono`, `sa-sr-only`. Mise en page : `sa-grid`, `sa-stack`, `sa-divider`. Valeur Sora : `sa-kpi__value`. Identifiant de dossier : `sa-mono` ou `sa-row-link`. Cellules : `sa-cell-main` / `sa-cell-sub`.
