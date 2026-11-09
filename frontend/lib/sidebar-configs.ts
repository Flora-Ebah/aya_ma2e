/**
 * Configuration déclarative du menu latéral MA2E (modèle POC GS2E).
 *
 * Chaque groupe est une section repliable (accordéon, 2 groupes ouverts au
 * maximum). Les icônes sont des noms du sprite HugeIcons
 * (public/design/icons.svg). Le filtrage RBAC se fait via `requiredModule`
 * (permission `read` du module dans le profil utilisateur).
 */

export type NavBadge = "a_traiter";

export type NavItem = {
  href: string;
  label: string;
  /** Nom d'icône du sprite HugeIcons. */
  icon: string;
  /** Préfixes supplémentaires qui maintiennent l'item actif dans la sidebar. */
  activePrefixes?: string[];
  /** Compteur affiché à droite (alimenté par les stats dossiers). */
  badge?: NavBadge;
};

export type NavGroup = {
  key: string;
  label: string;
  /** Icône du groupe (barre basse mobile, lien direct). */
  icon?: string;
  items?: NavItem[];
  /** Entrée directe (sans sous-items). */
  href?: string;
  activePrefixes?: string[];
  /** Module RBAC requis pour afficher ce groupe. Absent = toujours visible. */
  requiredModule?: "validation" | "reporting" | "administration" | "audit" | "conformite";
};

export const MAIN_NAV_GROUPS: NavGroup[] = [
  {
    key: "workspace",
    label: "Espace de travail",
    icon: "folder-01",
    activePrefixes: ["/dossiers", "/reporting", "/qr-code"],
    requiredModule: "validation",
    items: [
      { href: "/dossiers", label: "Dossiers", icon: "folder-01", activePrefixes: ["/dossiers"], badge: "a_traiter" },
      { href: "/reporting", label: "Reporting", icon: "chart-line-data-01" },
      { href: "/qr-code", label: "Accès QR", icon: "qr-code" },
    ],
  },
  {
    key: "chatbot",
    label: "Pilotage du chatbot",
    icon: "robot-01",
    activePrefixes: ["/assistante"],
    requiredModule: "administration",
    items: [
      { href: "/assistante/parcours", label: "Parcours", icon: "hierarchy-square-02" },
      { href: "/assistante/listes", label: "Listes de valeurs", icon: "list-view" },
      { href: "/assistante/connaissances", label: "Base de connaissances", icon: "book-open-01" },
    ],
  },
  {
    key: "administration",
    label: "Administration",
    icon: "shield-user",
    activePrefixes: ["/administration"],
    requiredModule: "administration",
    items: [
      { href: "/administration/utilisateurs", label: "Utilisateurs", icon: "user-settings-01" },
      { href: "/administration/roles", label: "Rôles & permissions", icon: "shield-user" },
      { href: "/administration/securite", label: "Sécurité & ARTCI", icon: "security-check" },
      { href: "/administration/integrations", label: "Intégrations externes", icon: "plug-01" },
    ],
  },
  {
    key: "audit",
    label: "Journal d'audit",
    icon: "audit-01",
    href: "/conformite/audit",
    activePrefixes: ["/conformite/audit"],
    requiredModule: "conformite",
  },
  {
    key: "settings",
    label: "Paramètres",
    icon: "settings-02",
    activePrefixes: ["/parametres"],
    items: [
      { href: "/parametres/general", label: "Paramètres généraux", icon: "settings-02" },
      { href: "/parametres/profil", label: "Mon profil", icon: "user-circle" },
    ],
  },
];
