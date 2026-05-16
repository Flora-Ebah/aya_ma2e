const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "ma2e_token";
const USER_KEY = "ma2e_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function setUser(user: any) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser(): any | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(USER_KEY);
  return v ? JSON.parse(v) : null;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path: string, opts: RequestInit = {}): Promise<any> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as any),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...opts, headers });
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
  me: () => request("/api/me"),
  listTenants: () => request("/api/tenants"),
  listDossiers: (tenantId?: string, status?: string) => {
    const params = new URLSearchParams();
    if (tenantId) params.set("tenant_id", tenantId);
    if (status) params.set("status", status);
    const q = params.toString();
    return request(`/api/dossiers${q ? "?" + q : ""}`);
  },
  getDossier: (id: string) => request(`/api/dossiers/${id}`),
  getStats: (tenantId?: string) =>
    request(`/api/dossiers/stats${tenantId ? `?tenant_id=${tenantId}` : ""}`),
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
  listKnowledgeSources: (tenantId?: string) =>
    request(`/api/knowledge/sources${tenantId ? `?tenant_id=${tenantId}` : ""}`),
  knowledgeStats: (tenantId?: string) =>
    request(`/api/knowledge/stats${tenantId ? `?tenant_id=${tenantId}` : ""}`),
  deleteKnowledgeSource: (id: string) =>
    request(`/api/knowledge/sources/${id}`, { method: "DELETE" }),
  streamIngestUrl: (url: string, maxPages: number, tenantId?: string) => {
    const t = getToken();
    const params = new URLSearchParams({
      url,
      max_pages: String(maxPages),
      ...(t ? { token: t } : {}),
      ...(tenantId ? { tenant_id: tenantId } : {}),
    });
    return `${API_URL}/api/knowledge/ingest/stream?${params.toString()}`;
  },

  // Audit
  listAuditLogs: (tenantId?: string, action?: string, actorType?: string) => {
    const params = new URLSearchParams();
    if (tenantId) params.set("tenant_id", tenantId);
    if (action) params.set("action", action);
    if (actorType) params.set("actor_type", actorType);
    const q = params.toString();
    return request(`/api/audit/logs${q ? "?" + q : ""}`);
  },
  auditStats: (tenantId?: string) =>
    request(`/api/audit/logs/stats${tenantId ? `?tenant_id=${tenantId}` : ""}`),
  listConversations: (tenantId?: string, channel?: string) => {
    const params = new URLSearchParams();
    if (tenantId) params.set("tenant_id", tenantId);
    if (channel) params.set("channel", channel);
    const q = params.toString();
    return request(`/api/audit/conversations${q ? "?" + q : ""}`);
  },
  getConversation: (id: string) => request(`/api/audit/conversations/${id}`),
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
