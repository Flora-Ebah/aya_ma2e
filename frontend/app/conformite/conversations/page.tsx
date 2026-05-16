"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, getUser } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FloatingChatButton from "@/components/FloatingChatButton";
import { useToast } from "@/components/ConfirmProvider";
import { IconMessage, IconUser, IconX } from "@/components/icons";

type Conversation = {
  id: string;
  channel: string;
  state: string;
  end_user_id: string;
  end_user_name: string | null;
  end_user_phone: string | null;
  messages_count: number;
  last_message_at: string | null;
  created_at: string;
  device_info: {
    user_agent?: string;
    ip?: string;
    lang?: string;
    session_id?: string;
  };
};

type Message = {
  id: string;
  direction: "inbound" | "outbound";
  content: string | null;
  media_url: string | null;
  extra: any;
  created_at: string;
};

type ConversationDetail = {
  id: string;
  channel: string;
  state: string;
  end_user: { id: string; name: string | null; phone: string | null };
  context: any;
  messages: Message[];
  created_at: string;
  updated_at: string;
};

const CHANNEL_LABEL: Record<string, { label: string; tone: string }> = {
  whatsapp: { label: "WhatsApp", tone: "bg-[#25D366]/10 text-[#1A6B3F] border-[#25D366]/30" },
  web: { label: "Chat Web", tone: "bg-primary-50 text-primary-700 border-primary-200" },
  telegram: { label: "Telegram", tone: "bg-blue-50 text-blue-700 border-blue-200" },
};

function parseUA(ua?: string): string {
  if (!ua) return "—";
  const lower = ua.toLowerCase();
  let device = "Desktop";
  if (/mobile|android|iphone|ipad/.test(lower)) device = "Mobile";
  let os = "Unknown";
  if (/android/.test(lower)) os = "Android";
  else if (/iphone|ipad|ios/.test(lower)) os = "iOS";
  else if (/windows/.test(lower)) os = "Windows";
  else if (/mac os/.test(lower)) os = "macOS";
  else if (/linux/.test(lower)) os = "Linux";
  let browser = "—";
  if (/edg\//.test(lower)) browser = "Edge";
  else if (/chrome\//.test(lower)) browser = "Chrome";
  else if (/firefox/.test(lower)) browser = "Firefox";
  else if (/safari/.test(lower)) browser = "Safari";
  return `${device} · ${os} · ${browser}`;
}

export default function ConversationsPage() {
  const router = useRouter();
  const toast = useToast();
  const [user, setUser] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [channelFilter, setChannelFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setUser(getUser());
    boot();
  }, [router]);

  async function boot() {
    try {
      const tenantList = await api.listTenants();
      setTenants(tenantList);
      const u = getUser();
      const initial =
        u?.role === "super_admin"
          ? tenantList.find((t: any) => t.is_active)?.id ?? tenantList[0]?.id ?? ""
          : u?.tenant_id ?? "";
      setSelectedTenant(initial);
      await load(initial, "");
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  async function load(tenantId: string, channel: string) {
    setLoading(true);
    try {
      const u = getUser();
      const tid = u?.role === "super_admin" ? tenantId : undefined;
      const items = await api.listConversations(tid, channel || undefined);
      setConversations(items);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(id: string) {
    setDetailLoading(true);
    try {
      const d = await api.getConversation(id);
      setDetail(d);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar
        tenants={tenants}
        selectedTenant={selectedTenant}
        onTenantChange={(id) => {
          setSelectedTenant(id);
          load(id, channelFilter);
        }}
      />
      <FloatingChatButton />

      <main className="lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="mb-6">
            <div className="text-[10.5px] uppercase tracking-[0.14em] text-primary-600 font-semibold mb-1.5">
              Conformité ARTCI
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
              Conversations & traçabilité
            </h1>
            <p className="text-ink-500 mt-1 text-[14px] font-light">
              Suivi des échanges sociétaires sur WhatsApp et Chat Web · device · session.
            </p>
          </div>

          {/* Filtres */}
          <div className="bg-white border border-ink-100 rounded-sm p-3 mb-4 flex flex-wrap gap-2">
            <button
              onClick={() => {
                setChannelFilter("");
                load(selectedTenant, "");
              }}
              className={`px-3 py-1.5 rounded-sm text-[12.5px] font-medium transition border ${
                channelFilter === ""
                  ? "bg-primary-600 text-white border-primary-600"
                  : "bg-white text-ink-700 border-ink-200 hover:bg-ink-50"
              }`}
            >
              Tous les canaux ({conversations.length})
            </button>
            <button
              onClick={() => {
                setChannelFilter("whatsapp");
                load(selectedTenant, "whatsapp");
              }}
              className={`px-3 py-1.5 rounded-sm text-[12.5px] font-medium transition border ${
                channelFilter === "whatsapp"
                  ? "bg-[#25D366] text-white border-[#25D366]"
                  : "bg-white text-ink-700 border-ink-200 hover:bg-ink-50"
              }`}
            >
              WhatsApp
            </button>
            <button
              onClick={() => {
                setChannelFilter("web");
                load(selectedTenant, "web");
              }}
              className={`px-3 py-1.5 rounded-sm text-[12.5px] font-medium transition border ${
                channelFilter === "web"
                  ? "bg-primary-600 text-white border-primary-600"
                  : "bg-white text-ink-700 border-ink-200 hover:bg-ink-50"
              }`}
            >
              Chat Web
            </button>
          </div>

          {/* Liste */}
          <div className="bg-white border border-ink-100 rounded-sm overflow-hidden">
            {loading ? (
              <div className="p-12 text-center text-ink-400 text-[13px]">Chargement…</div>
            ) : conversations.length === 0 ? (
              <div className="p-12 text-center">
                <IconMessage size={28} className="text-ink-300 mx-auto mb-2" />
                <div className="text-ink-700 font-medium text-[14px]">Aucune conversation</div>
              </div>
            ) : (
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-[#F9FBFA] text-ink-500 text-[10px] uppercase tracking-[0.1em] font-semibold border-b border-ink-100">
                    <th className="text-left px-4 py-2.5">Sociétaire</th>
                    <th className="text-left px-4 py-2.5">Canal</th>
                    <th className="text-left px-4 py-2.5">État</th>
                    <th className="text-left px-4 py-2.5">Appareil</th>
                    <th className="text-left px-4 py-2.5">Messages</th>
                    <th className="text-left px-4 py-2.5">Dernier</th>
                    <th className="text-left px-4 py-2.5 w-12"></th>
                  </tr>
                </thead>
                <tbody>
                  {conversations.map((c) => {
                    const ch = CHANNEL_LABEL[c.channel] || {
                      label: c.channel,
                      tone: "bg-ink-100 text-ink-700 border-ink-200",
                    };
                    return (
                      <tr
                        key={c.id}
                        className="border-b border-ink-100 last:border-0 hover:bg-primary-50/40 cursor-pointer transition"
                        onClick={() => openDetail(c.id)}
                      >
                        <td className="px-4 py-3">
                          <div className="text-ink-900 font-medium text-[13px]">
                            {c.end_user_name || "—"}
                          </div>
                          <div className="text-[11px] text-ink-500 font-mono">
                            {c.end_user_phone || "—"}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`text-[10.5px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-sm border ${ch.tone}`}
                          >
                            {ch.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[12px] text-ink-700 font-mono">
                          {c.state}
                        </td>
                        <td className="px-4 py-3 text-[11.5px] text-ink-600 font-light">
                          {c.channel === "web" ? parseUA(c.device_info.user_agent) : "—"}
                        </td>
                        <td className="px-4 py-3 text-[12px] font-mono text-ink-700">
                          {c.messages_count}
                        </td>
                        <td className="px-4 py-3 text-[11.5px] text-ink-500 font-light">
                          {c.last_message_at
                            ? new Date(c.last_message_at).toLocaleString("fr-FR", {
                                dateStyle: "short",
                                timeStyle: "short",
                              })
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-ink-300">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M9 18l6-6-6-6" />
                          </svg>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>

      {/* Drawer de détail */}
      {detail && (
        <div
          className="fixed inset-0 bg-ink-900/40 backdrop-blur-sm z-50 flex justify-end"
          onClick={() => setDetail(null)}
        >
          <div
            className="bg-white w-full max-w-2xl h-full overflow-y-auto border-l border-ink-100 animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-ink-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <div className="text-[11px] uppercase tracking-[0.14em] text-ink-400 font-semibold">
                  Conversation
                </div>
                <div className="text-[14px] font-semibold text-ink-900">
                  {detail.end_user.name || detail.end_user.phone || "—"}
                </div>
              </div>
              <button
                onClick={() => setDetail(null)}
                className="w-8 h-8 flex items-center justify-center text-ink-400 hover:text-ink-900 hover:bg-ink-100 rounded-sm transition"
              >
                <IconX size={16} />
              </button>
            </div>

            {/* Meta info */}
            <div className="px-6 py-4 border-b border-ink-100 grid grid-cols-2 gap-3 text-[12.5px]">
              <Meta label="Canal" value={detail.channel} mono />
              <Meta label="État" value={detail.state} mono />
              <Meta label="Téléphone" value={detail.end_user.phone || "—"} mono />
              <Meta label="Langue" value={detail.context?.lang || "fr"} />
              {detail.channel === "web" && (
                <>
                  <Meta
                    label="Appareil"
                    value={parseUA(detail.context?.user_agent)}
                    cols={2}
                  />
                  <Meta
                    label="Session"
                    value={detail.context?.session_id?.slice(0, 16) + "…" || "—"}
                    mono
                    cols={2}
                  />
                </>
              )}
              <Meta
                label="Créée"
                value={new Date(detail.created_at).toLocaleString("fr-FR")}
                cols={2}
              />
            </div>

            {/* Messages */}
            <div className="px-6 py-4 space-y-3">
              <div className="text-[11px] uppercase tracking-[0.14em] text-ink-500 font-semibold mb-2">
                Messages · {detail.messages.length}
              </div>
              {detail.messages.length === 0 && (
                <div className="text-ink-400 text-[12.5px] font-light italic text-center py-6">
                  Aucun message dans cette conversation.
                </div>
              )}
              {detail.messages.map((m) => {
                const inbound = m.direction === "inbound";
                return (
                  <div
                    key={m.id}
                    className={`flex ${inbound ? "justify-start" : "justify-end"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-[12px] px-3 py-2 text-[13px] ${
                        inbound
                          ? "bg-ink-100 text-ink-900 rounded-tl-[4px]"
                          : "bg-primary-600 text-white rounded-tr-[4px]"
                      }`}
                    >
                      <div className="whitespace-pre-wrap leading-relaxed">
                        {m.content || (m.media_url ? "[Média]" : "—")}
                      </div>
                      <div
                        className={`text-[10px] mt-1 ${
                          inbound ? "text-ink-500" : "text-white/70"
                        } text-right`}
                      >
                        {new Date(m.created_at).toLocaleTimeString("fr-FR", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                        {m.extra?.source === "notification" && (
                          <span className="ml-2 italic">notif auto</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {detailLoading && (
        <div className="fixed inset-0 bg-ink-900/30 z-40 flex items-center justify-center pointer-events-none">
          <div className="bg-white rounded-sm px-4 py-3 shadow-floating text-[13px]">
            Chargement…
          </div>
        </div>
      )}
    </div>
  );
}

function Meta({
  label,
  value,
  mono = false,
  cols = 1,
}: {
  label: string;
  value: string;
  mono?: boolean;
  cols?: number;
}) {
  return (
    <div className={cols === 2 ? "col-span-2" : ""}>
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-400 font-semibold">
        {label}
      </div>
      <div
        className={`text-ink-900 font-medium mt-0.5 truncate ${
          mono ? "font-mono text-[12px]" : "text-[13px]"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
