const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Authentification — Phase 2 : cookie httpOnly + jeton CSRF (double-submit).
 *
 * Le JWT est stocké dans un cookie `ma2e_token` httpOnly côté serveur : le
 * navigateur l'envoie automatiquement sur chaque requête `credentials:
 * "include"`, et JavaScript ne peut PAS le lire (immunité XSS).
 *
 * Un cookie `ma2e_csrf` (non-httpOnly) contient un jeton aléatoire régénéré
 * à chaque connexion. Le frontend le lit et le renvoie en header
 * `X-CSRF-Token` sur toute mutation (POST/PUT/DELETE/PATCH). Le middleware
 * backend refuse la requête si les deux ne correspondent pas.
 *
 * Aucune donnée sensible n'est stockée dans `localStorage`. Le profil
 * utilisateur est ré-hydraté à chaque page via `/api/me`.
 */
const CSRF_COOKIE = "ma2e_csrf";

/**
 * @deprecated — Phase 2 : le token JWT est désormais dans un cookie httpOnly.
 * Cette fonction retourne toujours `null`. Elle reste exportée uniquement pour
 * ne pas casser les 25+ pages qui l'importent encore. À supprimer dans un
 * refactor futur : les requêtes utilisent maintenant `credentials: "include"`
 * qui envoie le cookie automatiquement.
 */
export function getToken(): string | null {
  return null;
}

/** @deprecated — no-op, le cookie httpOnly est posé par le backend au login. */
export function setToken(_token: string): void {
  /* intentionnellement vide */
}

/**
 * @deprecated — Le profil est désormais géré en mémoire par
 * `<CurrentUserProvider>` (voir `components/CurrentUserProvider.tsx`).
 * Rien n'est persisté côté client — le fetch `/api/me` se fait au montage.
 * Ces fonctions restent en no-op pour compat avec les appels existants.
 */
export function setUser(_user: unknown): void {
  /* no-op — voir CurrentUserProvider */
}

/** @deprecated — utiliser `useCurrentUser()` du CurrentUserProvider. */
export function getUser(): null {
  return null;
}

function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const raw = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${CSRF_COOKIE}=`));
  return raw ? decodeURIComponent(raw.slice(CSRF_COOKIE.length + 1)) : null;
}

/**
 * Termine la session côté serveur (efface les cookies httpOnly) puis
 * purge toute clé locale que l'app aurait pu laisser (chat session,
 * préférences UI, caches). Idempotent — safe à appeler sans être connecté.
 */
export async function logout(): Promise<void> {
  try {
    await fetch(`${API_URL}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Réseau KO : on nettoie quand même côté client.
  }
  try {
    if (typeof localStorage !== "undefined") {
      const keys: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith("ma2e_")) keys.push(k);
      }
      keys.forEach((k) => localStorage.removeItem(k));
    }
    if (typeof sessionStorage !== "undefined") sessionStorage.clear();
  } catch {
    // localStorage bloqué (mode privé strict) : ignore.
  }
}

/** Endpoints d'authentification exclus du refresh+retry automatique.
 *  Sinon un mauvais mot de passe sur /login boucle vers /login, et un
 *  /api/auth/refresh en 401 doit rester en 401 (pas de re-refresh récursif). */
const AUTH_PATHS = [
  "/api/auth/login",
  "/api/auth/mfa/verify",
  "/api/auth/ad/login",
  "/api/auth/logout",
  "/api/auth/refresh",
  // /api/me est utilisé au montage pour hydrater le profil : on veut qu'un 401
  // remonte tel quel (session absente = état légitime sur /login).
  "/api/me",
];

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/**
 * Refresh en cours (verrou global). Si N requêtes prennent 401 simultanément,
 * on ne déclenche QU'UN SEUL /api/auth/refresh — les autres attendent le
 * même résultat. Sans ce verrou, le premier refresh consommerait le jti,
 * les suivants échoueraient et déclencheraient un faux logout.
 */
let refreshPromise: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_URL}/api/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      // Libère le verrou APRÈS que tous les callers en attente aient lu le résultat.
      // On defer la remise à null pour éviter qu'un caller tardif ne relance.
      setTimeout(() => { refreshPromise = null; }, 50);
    }
  })();
  return refreshPromise;
}

async function doFetch(path: string, opts: RequestInit): Promise<Response> {
  const method = (opts.method || "GET").toUpperCase();
  const isFormData =
    typeof FormData !== "undefined" && opts.body instanceof FormData;
  const headers: Record<string, string> = {
    // Pour les uploads multipart, laisser fetch poser son propre boundary.
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(opts.headers as any),
  };
  // Header CSRF sur toute mutation, si on a un cookie CSRF (utilisateur connecté).
  if (UNSAFE_METHODS.has(method)) {
    const csrf = readCsrfCookie();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  return fetch(`${API_URL}${path}`, { ...opts, headers, credentials: "include" });
}

async function request(path: string, opts: RequestInit = {}): Promise<any> {
  let res = await doFetch(path, opts);

  // Session expirée / access token invalide → tente un refresh silencieux.
  // Si le refresh réussit, on rejoue la requête originale UNE fois.
  // Sinon, purge locale + retour login.
  if (res.status === 401 && typeof window !== "undefined") {
    const isAuthEndpoint = AUTH_PATHS.some((p) => path.startsWith(p));
    if (!isAuthEndpoint) {
      const refreshed = await attemptRefresh();
      if (refreshed) {
        res = await doFetch(path, opts);
      }
      if (res.status === 401) {
        // Si on est déjà sur /login, ne pas re-router (sinon boucle infinie).
        if (window.location.pathname.startsWith("/login")) {
          throw new Error("401: non authentifié");
        }
        await logout();
        const currentPath = window.location.pathname + window.location.search;
        window.location.href = `/login?expired=1&next=${encodeURIComponent(currentPath)}`;
        throw new Error("401: session expirée");
      }
    }
  }

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  mfaVerify: (challengeToken: string, code: string) =>
    request("/api/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_token: challengeToken, code }),
    }),
  adLogin: (email: string) =>
    request("/api/auth/ad/login", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  mfaStatus: () => request("/api/users/me/mfa/status"),
  mfaSetup: () => request("/api/users/me/mfa/setup", { method: "POST", body: "{}" }),
  mfaEnable: (code: string) =>
    request("/api/users/me/mfa/enable", { method: "POST", body: JSON.stringify({ code }) }),
  mfaDisable: (code: string) =>
    request("/api/users/me/mfa/disable", { method: "POST", body: JSON.stringify({ code }) }),
  adminMfaDisable: (userId: string) =>
    request(`/api/users/${userId}/mfa/disable`, { method: "POST", body: "{}" }),
  me: () => request("/api/me"),
  listDossiers: (filters?: {
    status?: string;
    statuses?: string[];
    employeur_code?: string;
    matricule?: string;
    agent_id?: string;
    min_ocr_score?: number;
    max_ocr_score?: number;
    priority_only?: boolean;
    overdue_only?: boolean;
    since?: string;
    until?: string;
    sort?: string;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v === undefined || v === null || v === "" || v === false) return;
        if (Array.isArray(v)) {
          if (v.length) params.set(k, v.join(","));
        } else {
          params.set(k, String(v));
        }
      });
    }
    const q = params.toString();
    return request(`/api/dossiers${q ? "?" + q : ""}`);
  },
  getDossier: (id: string) => request(`/api/dossiers/${id}`),
  getStats: () => request(`/api/dossiers/stats`),
  validateDossier: (id: string) =>
    request(`/api/dossiers/${id}/validate`, { method: "POST", body: "{}" }),
  rejectDossier: (id: string, motive: string) =>
    request(`/api/dossiers/${id}/reject`, { method: "POST", body: JSON.stringify({ motive }) }),
  complementDossier: (id: string, request_text: string) =>
    request(`/api/dossiers/${id}/complement`, {
      method: "POST",
      body: JSON.stringify({ request_text }),
    }),

  // Knowledge base
  listKnowledgeSources: () => request(`/api/knowledge/sources`),
  knowledgeStats: () => request(`/api/knowledge/stats`),
  deleteKnowledgeSource: (id: string) =>
    request(`/api/knowledge/sources/${id}`, { method: "DELETE" }),
  uploadKnowledgeFile: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/api/knowledge/upload", { method: "POST", body: fd as any });
  },
  listKnowledgeExtensions: () => request("/api/knowledge/supported-extensions"),
  streamIngestUrl: (url: string, maxPages: number) => {
    const params = new URLSearchParams({
      url,
      max_pages: String(maxPages),
    });
    return `${API_URL}/api/knowledge/ingest/stream?${params.toString()}`;
  },

  // Audit
  listAuditLogs: (action?: string, actorType?: string) => {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (actorType) params.set("actor_type", actorType);
    const q = params.toString();
    return request(`/api/audit/logs${q ? "?" + q : ""}`);
  },
  auditStats: () => request(`/api/audit/logs/stats`),
  listConversations: (channel?: string) => {
    const params = new URLSearchParams();
    if (channel) params.set("channel", channel);
    const q = params.toString();
    return request(`/api/audit/conversations${q ? "?" + q : ""}`);
  },
  getConversation: (id: string) => request(`/api/audit/conversations/${id}`),

  // ============ Settings (Phase 2) ============
  listSettingCategories: () => request("/api/settings/categories"),
  getSettingsCategory: (category: string) =>
    request(`/api/settings/${category}`),
  updateSetting: (category: string, key: string, value: any, change_reason?: string) =>
    request(`/api/settings/${category}/${key}`, {
      method: "PUT",
      body: JSON.stringify({ value, change_reason }),
    }),
  getSettingHistory: (category: string, key: string, limit = 50) =>
    request(`/api/settings/${category}/${key}/history?limit=${limit}`),
  rollbackSetting: (category: string, key: string, version: number) =>
    request(`/api/settings/${category}/${key}/rollback/${version}`, {
      method: "POST",
      body: "{}",
    }),

  // ============ Message templates (Phase 2) ============
  listTemplateGroups: () => request("/api/templates/groups"),
  listTemplates: (group?: string, language = "fr") => {
    const params = new URLSearchParams({ language });
    if (group) params.set("group", group);
    return request(`/api/templates?${params.toString()}`);
  },
  getTemplate: (code: string, language = "fr") =>
    request(`/api/templates/${encodeURIComponent(code)}?language=${language}`),
  upsertTemplate: (
    code: string,
    payload: { content: string; subject?: string | null; channel?: string | null; change_reason?: string | null },
    language = "fr",
  ) =>
    request(`/api/templates/${encodeURIComponent(code)}?language=${language}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  previewTemplate: (
    code: string,
    variables: Record<string, string>,
    content?: string,
    language = "fr",
  ) =>
    request(`/api/templates/${encodeURIComponent(code)}/preview?language=${language}`, {
      method: "POST",
      body: JSON.stringify({ variables, content }),
    }),
  resetTemplate: (code: string, language = "fr") =>
    request(`/api/templates/${encodeURIComponent(code)}/reset?language=${language}`, {
      method: "POST",
      body: "{}",
    }),
  getTemplateHistory: (code: string, language = "fr", limit = 50) =>
    request(
      `/api/templates/${encodeURIComponent(code)}/history?language=${language}&limit=${limit}`,
    ),
  rollbackTemplate: (code: string, targetVersion: number, language = "fr") =>
    request(
      `/api/templates/${encodeURIComponent(code)}/rollback/${targetVersion}?language=${language}`,
      { method: "POST", body: "{}" },
    ),

  // ============ Users (Phase 2) ============
  listUsers: (includeInactive = true) => {
    const params = new URLSearchParams({ include_inactive: String(includeInactive) });
    return request(`/api/users?${params.toString()}`);
  },
  getUser: (id: string) => request(`/api/users/${id}`),
  createUser: (payload: {
    email: string;
    name: string;
    role: "super_admin" | "tenant_admin" | "agent";
    auth_method?: "password" | "ad";
    password?: string | null;
  }) => request("/api/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (
    id: string,
    payload: { name?: string; role?: string; is_active?: boolean },
  ) =>
    request(`/api/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  resetUserPassword: (id: string, newPassword: string) =>
    request(`/api/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword }),
    }),
  changeMyPassword: (currentPassword: string, newPassword: string) =>
    request("/api/users/me/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),

  // ============ Security / ARTCI (Phase 2) ============
  getSecurityPolicy: () => request("/api/security/policy"),
  retentionPreview: () => request("/api/security/retention/preview"),
  exportDossierRgpd: (dossierId: string) =>
    request(`/api/security/dossiers/${dossierId}/export`),

  // ============ Stats / Reporting (Phase 2) ============
  statsOverview: (periodDays = 30) =>
    request(`/api/stats/overview?period_days=${periodDays}`),
  statsTimeline: (periodDays = 30) =>
    request(`/api/stats/timeline?period_days=${periodDays}`),
  statsByChannel: () => request(`/api/stats/by-channel`),
  statsRejectionReasons: (topN = 10) =>
    request(`/api/stats/rejection-reasons?top_n=${topN}`),
  statsAgentsPerformance: (periodDays = 90, topN = 10) =>
    request(`/api/stats/agents-performance?period_days=${periodDays}&top_n=${topN}`),
  statsOcrQuality: (periodDays = 90) =>
    request(`/api/stats/ocr-quality?period_days=${periodDays}`),
  statsConversionFunnel: (periodDays = 30) =>
    request(`/api/stats/conversion-funnel?period_days=${periodDays}`),

  // ============ Integrations (Phase 2) ============
  referentialVerify: (employeur: string, matricule: string) => {
    const params = new URLSearchParams({ employeur, matricule });
    return request(`/api/integrations/referential/verify?${params.toString()}`);
  },
  webhookTest: () =>
    request("/api/integrations/webhooks/test", { method: "POST", body: "{}" }),
  webhookDeliveries: (limit = 50) =>
    request(`/api/integrations/webhooks/deliveries?limit=${limit}`),
  webhookRetry: (deliveryId: string) =>
    request(`/api/integrations/webhooks/deliveries/${deliveryId}/retry`, {
      method: "POST",
      body: "{}",
    }),
  // Services activables (OCR, OTP, notifications) — section "Services & IA"
  listServices: () => request("/api/integrations/services"),
  toggleService: (key: string, enabled: boolean) =>
    request(`/api/integrations/services/${key}/toggle`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  // Actions de workflow enrichies avec métadonnées (service lié, branches)
  listWorkflowActionsDetailed: () =>
    request("/api/workflows/_meta/actions/detailed"),

  // ============ Employeurs CRUD (US-05) ============
  listEmployeurs: (includeInactive = true) =>
    request(`/api/employeurs?include_inactive=${includeInactive}`),
  createEmployeur: (code: string, name: string) =>
    request("/api/employeurs", { method: "POST", body: JSON.stringify({ code, name }) }),
  updateEmployeur: (id: string, payload: { name?: string; is_active?: boolean }) =>
    request(`/api/employeurs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteEmployeur: (id: string) =>
    request(`/api/employeurs/${id}`, { method: "DELETE" }),

  // ============ Collaborateurs (référentiel ERANOVE) ============
  listCollaborateurs: (filters?: {
    employeur_code?: string;
    search?: string;
    statut?: string;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params.set(k, String(v));
      });
    }
    const q = params.toString();
    return request(`/api/collaborateurs${q ? "?" + q : ""}`);
  },
  createCollaborateur: (payload: any) =>
    request("/api/collaborateurs", { method: "POST", body: JSON.stringify(payload) }),
  updateCollaborateur: (id: string, payload: any) =>
    request(`/api/collaborateurs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteCollaborateur: (id: string) =>
    request(`/api/collaborateurs/${id}`, { method: "DELETE" }),

  // ============ Imports (US-37) ============
  listImportTargets: () => request("/api/imports/targets"),
  downloadImportTemplate: (target: string): string => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${base}/api/imports/template/${target}`;
  },
  uploadImport: async (target: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const headers: Record<string, string> = {};
    const csrf = readCsrfCookie();
    if (csrf) headers["X-CSRF-Token"] = csrf;
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${base}/api/imports/${target}`, {
      method: "POST",
      body: form,
      credentials: "include",
      headers,
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status}: ${txt}`);
    }
    return res.json();
  },

  // ============ Exports Excel/PDF (US-25, US-27) ============
  // Le cookie httpOnly est envoyé automatiquement par le navigateur lors
  // d'une navigation <a href> vers ces URLs (même origine). Plus besoin
  // de propager le token en query string.
  exportDossiersUrl: (filters?: {
    status?: string;
    employeur_code?: string;
    since?: string;
    until?: string;
  }) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params.set(k, String(v));
      });
    }
    return `${base}/api/dossiers/export.xlsx${params.toString() ? "?" + params : ""}`;
  },
  exportAuditUrl: (filters?: { action?: string; actor_type?: string; since?: string; until?: string }) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params.set(k, String(v));
      });
    }
    const token = getToken();
    if (token) params.set("token", token);
    return `${base}/api/audit/logs/export.csv${params.toString() ? "?" + params : ""}`;
  },
  exportStatsPdfUrl: (periodDays: number) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const params = new URLSearchParams({ period_days: String(periodDays) });
    const token = getToken();
    if (token) params.set("token", token);
    return `${base}/api/stats/overview.pdf?${params.toString()}`;
  },

  // ============ Roles RBAC (US-03, US-04) ============
  rolesPermissionsSchema: () => request("/api/roles/permissions"),
  listRoles: () => request("/api/roles"),
  getRole: (id: string) => request(`/api/roles/${id}`),
  createRole: (payload: { name: string; description?: string; permissions: any }) =>
    request("/api/roles", { method: "POST", body: JSON.stringify(payload) }),
  updateRole: (id: string, payload: { name?: string; description?: string; permissions?: any; is_active?: boolean }) =>
    request(`/api/roles/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteRole: (id: string) => request(`/api/roles/${id}`, { method: "DELETE" }),
  seedDefaultRoles: () => request("/api/roles/seed-defaults", { method: "POST", body: "{}" }),
  listUserRoles: (userId: string) => request(`/api/users/${userId}/roles`),
  assignRoleToUser: (userId: string, roleId: string) =>
    request(`/api/users/${userId}/roles/${roleId}`, { method: "POST", body: "{}" }),
  revokeRoleFromUser: (userId: string, roleId: string) =>
    request(`/api/users/${userId}/roles/${roleId}`, { method: "DELETE" }),
  myPermissions: () => request("/api/me/permissions"),

  // ============ Anonymisation (US-28) + ARTCI contact (US-29) ============
  anonymizeDossier: (dossierId: string, reason: string) =>
    request(`/api/security/dossiers/${dossierId}/anonymize`, {
      method: "POST",
      body: JSON.stringify({ confirm: true, reason }),
    }),
  deleteDossier: (dossierId: string) =>
    request(`/api/dossiers/${dossierId}`, { method: "DELETE" }),
  fichePdfUrl: (dossierId: string) =>
    `${API_URL}/api/dossiers/${dossierId}/fiche.pdf`,
  bulkFichesPdfUrl: (ids: string[]) =>
    `${API_URL}/api/dossiers/fiches.pdf?ids=${ids.join(",")}`,
  // Endpoint public (pas d'auth requise — utilisé depuis /artci)
  artciContact: async (payload: {
    full_name: string;
    email: string;
    subject: string;
    message: string;
    request_type: string;
  }) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${base}/api/security/artci/contact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status}: ${txt}`);
    }
    return res.json();
  },

  // ============ Workflows (parcours conversationnel dynamique) ============
  listWorkflows: () => request("/api/workflows"),
  getActiveWorkflow: () => request("/api/workflows/active"),
  getWorkflow: (id: string) => request(`/api/workflows/${id}`),
  createWorkflow: (payload: {
    name: string;
    description?: string;
    start_step_code?: string | null;
  }) => request("/api/workflows", { method: "POST", body: JSON.stringify(payload) }),
  updateWorkflow: (
    id: string,
    payload: { name?: string; description?: string; start_step_code?: string | null },
  ) =>
    request(`/api/workflows/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  activateWorkflow: (id: string) =>
    request(`/api/workflows/${id}/activate`, { method: "POST", body: "{}" }),
  deleteWorkflow: (id: string) =>
    request(`/api/workflows/${id}`, { method: "DELETE" }),
  createWorkflowStep: (workflowId: string, payload: any) =>
    request(`/api/workflows/${workflowId}/steps`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateWorkflowStep: (workflowId: string, stepId: string, payload: any) =>
    request(`/api/workflows/${workflowId}/steps/${stepId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteWorkflowStep: (workflowId: string, stepId: string) =>
    request(`/api/workflows/${workflowId}/steps/${stepId}`, { method: "DELETE" }),
  reorderWorkflowSteps: (workflowId: string, orderedCodes: string[]) =>
    request(`/api/workflows/${workflowId}/steps/reorder`, {
      method: "POST",
      body: JSON.stringify({ ordered_codes: orderedCodes }),
    }),
  reorderWorkflows: (orderedIds: string[]) =>
    request(`/api/workflows/reorder`, {
      method: "POST",
      body: JSON.stringify({ ordered_ids: orderedIds }),
    }),
  setWorkflowActive: (id: string, active: boolean) =>
    request(`/api/workflows/${id}/set-active`, {
      method: "POST",
      body: JSON.stringify({ active }),
    }),
  simulateWorkflow: (
    workflowId: string,
    payload: {
      current_step_code: string | null;
      user_input: string | null;
      context: Record<string, any>;
    },
  ) =>
    request(`/api/workflows/${workflowId}/simulate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listWorkflowActions: () => request("/api/workflows/_meta/actions"),

  // ============ Parcours IA (upload Word/PDF/TXT + extraction LLM) ============
  listParcoursVersions: () => request("/api/parcours/versions"),
  getParcoursVersionDocument: (wfId: string) =>
    request(`/api/parcours/versions/${wfId}/document`),
  extractParcoursUpload: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/api/parcours/extract", { method: "POST", body: fd as any });
  },
  applyParcoursDocument: (document: any) =>
    request("/api/parcours/apply", {
      method: "POST",
      body: JSON.stringify({ document }),
    }),
  activateParcoursVersion: (id: string) =>
    request(`/api/parcours/versions/${id}/activate`, { method: "POST", body: "{}" }),
  deleteParcoursVersion: (id: string) =>
    request(`/api/parcours/versions/${id}`, { method: "DELETE" }),

  // ============ Référentiels (listes fermées utilisées par les parcours IA) ============
  listReferenceLists: () => request("/api/reference-lists"),
  createReferenceList: (payload: {
    key: string;
    label: string;
    description?: string | null;
    aliases?: string[];
    items: Array<{ code?: string | null; label: string; synonyms?: string[] }>;
    allow_other?: boolean;
  }) =>
    request("/api/reference-lists", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateReferenceList: (
    id: string,
    payload: Partial<{
      label: string;
      description: string | null;
      aliases: string[];
      items: Array<{ code?: string | null; label: string; synonyms?: string[] }>;
      allow_other: boolean;
    }>,
  ) =>
    request(`/api/reference-lists/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteReferenceList: (id: string) =>
    request(`/api/reference-lists/${id}`, { method: "DELETE" }),
};

export const STATUS_LABELS: Record<string, string> = {
  en_cours: "En cours",
  soumis: "Soumis",
  en_validation: "En validation",
  valide: "Validé",
  rejete: "Rejeté",
  complement_requis: "Complément requis",
};

export const STATUS_COLORS: Record<string, string> = {
  en_cours: "bg-slate-500/20 text-slate-300 border-slate-500/40",
  soumis: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  en_validation: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  valide: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  rejete: "bg-red-500/20 text-red-300 border-red-500/40",
  complement_requis: "bg-purple-500/20 text-purple-300 border-purple-500/40",
};

export const GATE_LABELS: Record<string, string> = {
  artci: "Consentement ARTCI",
  ocr_validation: "Validation OCR",
  certification_finale: "Certification finale",
  communications: "Communications",
};
