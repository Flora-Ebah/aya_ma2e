"use client";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import {
  IconActivity,
  IconArrowUp,
  IconClock,
  IconEdit,
  IconFileText,
  IconImage,
  IconPaperclip,
  IconShield,
  IconUser,
  IconX,
} from "@/components/icons";
import { useConfirm } from "@/components/ConfirmProvider";

const QUICK_TIPS = [
  {
    icon: IconClock,
    text: "Combien de temps prend l'enrôlement digital ?",
    payload: "Combien de temps prend l'enrôlement ?",
  },
  {
    icon: IconFileText,
    text: "Quels documents sont acceptés ?",
    payload: "Quels documents sont acceptés ?",
  },
  {
    icon: IconShield,
    text: "Comment sont protégées mes données ?",
    payload: "Comment mes données sont protégées ?",
  },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_KEY = "ma2e_chat_session";
const TENANT_SLUG = "ma2e";

type Message = {
  id: string;
  direction: "in" | "out";
  text: string;
  timestamp: number;
};

function uuid() {
  return crypto.randomUUID
    ? crypto.randomUUID()
    : `web-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function greeting(hour: number) {
  if (hour >= 5 && hour < 12) return "Bonjour";
  if (hour >= 12 && hour < 18) return "Bon après-midi";
  return "Bonsoir";
}

export default function ChatPage() {
  const confirm = useConfirm();
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [avatarOk, setAvatarOk] = useState(true);
  const [pendingFile, setPendingFile] = useState<{
    name: string;
    size: number;
    type: string;
    url?: string;
    uploading: boolean;
  } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bootRef = useRef(false);
  const [now] = useState(() => new Date());

  useEffect(() => {
    if (bootRef.current) return;
    bootRef.current = true;
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = uuid();
      localStorage.setItem(SESSION_KEY, sid);
    }
    setSessionId(sid);

    const img = new window.Image();
    img.src = "/assistant-avatar.png";
    img.onerror = () => setAvatarOk(false);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading, pendingFile?.url]);

  useEffect(() => {
    if (!loading) {
      textareaRef.current?.focus();
    }
  }, [loading, messages.length]);

  function autoResize() {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }

  async function send(message: string, mediaUrl?: string) {
    if (!sessionId) return;
    if (!message.trim() && !mediaUrl) return;
    setError(null);
    setLoading(true);

    const displayText = mediaUrl
      ? message || `📎 ${pendingFile?.name || "Pièce jointe"}`
      : message;

    setMessages((prev) => [
      ...prev,
      { id: uuid(), direction: "in", text: displayText, timestamp: Date.now() },
    ]);

    try {
      const res = await fetch(`${API_URL}/webhooks/web/${TENANT_SLUG}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: message || "",
          media_url: mediaUrl,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { id: uuid(), direction: "out", text: data.reply, timestamp: Date.now() },
      ]);
    } catch (e: any) {
      setError(e.message || "Erreur de communication");
    } finally {
      setLoading(false);
    }
  }

  async function uploadFile(file: File) {
    if (!sessionId) return;
    setPendingFile({ name: file.name, size: file.size, type: file.type, uploading: true });
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("session_id", sessionId);
      const res = await fetch(`${API_URL}/webhooks/web/upload/${TENANT_SLUG}`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPendingFile({
        name: file.name,
        size: file.size,
        type: file.type,
        url: data.media_url,
        uploading: false,
      });
    } catch (e: any) {
      setError("Échec de l'envoi du fichier : " + (e.message || "erreur réseau"));
      setPendingFile(null);
    }
  }

  function onFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 10 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 10 Mo).");
      return;
    }
    uploadFile(f);
    e.target.value = "";
  }

  function onSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (loading) return;
    const text = input.trim();
    const mediaUrl = pendingFile?.url;
    if (!text && !mediaUrl) return;
    if (pendingFile?.uploading) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    send(text, mediaUrl);
    setPendingFile(null);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  }

  async function resetSession() {
    if (messages.length > 0) {
      const ok = await confirm({
        title: "Démarrer une nouvelle conversation ?",
        message: "Les messages actuels seront effacés. Cette action est irréversible.",
        confirmText: "Démarrer",
        cancelText: "Annuler",
        variant: "default",
        icon: "warn",
      });
      if (!ok) return;
    }
    localStorage.removeItem(SESSION_KEY);
    setMessages([]);
    const sid = uuid();
    localStorage.setItem(SESSION_KEY, sid);
    setSessionId(sid);
  }

  const hasMessages = messages.length > 0;
  const hello = greeting(now.getHours());

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-white via-primary-50/20 to-white">
      <main className="flex-1 flex flex-col">
        {hasMessages && (
          <div className="sticky top-0 z-20 bg-white/80 backdrop-blur-md">
            <div className="max-w-3xl mx-auto px-4 sm:px-6">
              <div className="py-3 flex items-center justify-between border-b border-ink-100">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-full overflow-hidden ring-2 ring-white shadow-sm">
                    <AssistantAvatar size={40} avatarOk={avatarOk} ring={false} />
                  </div>
                  <div className="text-[13px] font-medium text-ink-900">MA2E Assistant</div>
                </div>
                <button
                  onClick={resetSession}
                  className="w-10 h-10 rounded-full border border-ink-200 hover:bg-ink-50 hover:border-ink-300 flex items-center justify-center text-ink-700 hover:text-primary-700 transition"
                  title="Nouvelle conversation"
                  aria-label="Nouvelle conversation"
                >
                  <IconEdit size={15} />
                </button>
              </div>
            </div>
          </div>
        )}
        {!hasMessages ? (
          <WelcomeScreen
            hello={hello}
            avatarOk={avatarOk}
            onPick={(payload) => send(payload)}
            onReset={resetSession}
            disabled={loading}
          />
        ) : (
          <Transcript
            messages={messages}
            loading={loading}
            avatarOk={avatarOk}
            bottomRef={bottomRef}
          />
        )}

        <div className="sticky bottom-0 bg-gradient-to-t from-white via-white to-transparent pt-6 pb-4">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 w-full">
            {error && (
              <div className="mb-2 flex items-start gap-2 bg-red-50 border border-red-200 text-red-800 rounded-sm px-3 py-2 text-sm">
                {error}
              </div>
            )}
            <form
              onSubmit={onSubmit}
              className="bg-white border border-ink-200 hover:border-ink-300 focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 rounded-sm shadow-card transition"
            >
              {pendingFile && (
                <div className="px-3 pt-3">
                  <div className="inline-flex items-center gap-2 bg-primary-50 border border-primary-200 rounded-sm pl-2 pr-1 py-1.5 max-w-full">
                    <div className="w-7 h-7 rounded-sm bg-primary-100 text-primary-700 flex items-center justify-center shrink-0">
                      {pendingFile.type.startsWith("image/") ? (
                        <IconImage size={14} />
                      ) : (
                        <IconPaperclip size={14} />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[12px] font-medium text-ink-900 truncate">
                        {pendingFile.name}
                      </div>
                      <div className="text-[10px] text-ink-500 font-light">
                        {pendingFile.uploading
                          ? "Envoi en cours…"
                          : `${(pendingFile.size / 1024).toFixed(1)} Ko · prêt`}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setPendingFile(null)}
                      className="w-6 h-6 flex items-center justify-center rounded-sm text-ink-400 hover:text-red-600 hover:bg-red-50 transition shrink-0"
                      aria-label="Retirer"
                    >
                      <IconX size={12} />
                    </button>
                  </div>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,application/pdf"
                onChange={onFilePick}
                className="hidden"
              />
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  autoResize();
                }}
                onKeyDown={onKeyDown}
                rows={1}
                disabled={loading}
                placeholder="Comment puis-je vous aider aujourd'hui ?"
                className="w-full bg-transparent px-4 pt-2.5 pb-1 text-[14.5px] font-light text-ink-900 placeholder:text-ink-400 focus:outline-none resize-none disabled:opacity-50"
                style={{ minHeight: 38 }}
                autoFocus
              />
              <div className="flex items-center justify-between px-2.5 pb-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading || pendingFile?.uploading}
                  className="w-9 h-9 flex items-center justify-center rounded-full bg-ink-100 hover:bg-ink-200 text-ink-600 hover:text-ink-900 transition disabled:opacity-50"
                  title="Joindre une photo ou un PDF"
                  aria-label="Joindre un fichier"
                >
                  <IconPaperclip size={15} />
                </button>
                <button
                  type="submit"
                  disabled={loading || pendingFile?.uploading || (!input.trim() && !pendingFile?.url)}
                  className="w-9 h-9 flex items-center justify-center rounded-full bg-primary-600 hover:bg-primary-700 text-white shadow-sm disabled:bg-ink-300 disabled:cursor-not-allowed transition"
                  aria-label="Envoyer"
                >
                  <IconArrowUp size={16} />
                </button>
              </div>
            </form>
            <div className="flex items-center justify-between mt-2 px-1 text-[11px] text-ink-400 font-light">
              <span className="flex items-center gap-1.5">
                <IconShield size={11} />
                <span className="hidden sm:inline">L'assistant peut commettre des erreurs. Vérifiez les informations.</span>
                <span className="sm:hidden">Conforme loi 2013-450</span>
              </span>
              <span className="hidden sm:inline">
                <kbd className="font-mono bg-ink-100 px-1.5 py-0.5 rounded-sm text-[10px] font-normal">Shift + Entrée</kbd> pour saut de ligne
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function AssistantAvatar({ size = 32, avatarOk = true, ring = true }: { size?: number; avatarOk?: boolean; ring?: boolean }) {
  if (avatarOk) {
    return (
      <div
        className={`relative shrink-0 rounded-full overflow-hidden bg-white ${
          ring ? "ring-2 ring-white shadow-sm" : ""
        }`}
        style={{ width: size, height: size }}
      >
        <Image
          src="/assistant-avatar.png"
          alt="MA2E Assistant"
          width={size}
          height={size}
          className="w-full h-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      className={`shrink-0 rounded-full bg-gradient-to-br from-primary-400 via-primary-500 to-primary-700 text-white flex items-center justify-center font-semibold ${
        ring ? "ring-2 ring-white shadow-sm" : ""
      }`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      M
    </div>
  );
}

function WelcomeScreen({
  hello,
  avatarOk,
  onPick,
  onReset,
  disabled,
}: {
  hello: string;
  avatarOk: boolean;
  onPick: (payload: string) => void;
  onReset: () => void;
  disabled: boolean;
}) {
  return (
    <div className="flex-1 flex flex-col px-4 sm:px-6 pt-4 pb-6 w-full max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="w-12 h-12 rounded-full overflow-hidden ring-2 ring-white shadow-card">
          <AssistantAvatar size={48} avatarOk={avatarOk} ring={false} />
        </div>
        <button
          onClick={onReset}
          className="w-10 h-10 rounded-full border border-ink-200 hover:bg-ink-50 hover:border-ink-300 flex items-center justify-center text-ink-700 hover:text-primary-700 transition"
          title="Nouvelle conversation"
          aria-label="Nouvelle conversation"
        >
          <IconEdit size={15} />
        </button>
      </div>

      <h1 className="text-[26px] sm:text-3xl font-medium text-ink-900 tracking-tight leading-[1.2] mb-5">
        {hello},
        <br />
        Comment puis-je vous aider ?
      </h1>

      <div className="grid grid-cols-2 gap-2.5 mb-5">
        <button
          onClick={() => onPick("/identification")}
          disabled={disabled}
          className="row-span-2 relative bg-gradient-to-br from-primary-100 via-primary-200 to-primary-300 rounded-sm p-4 flex flex-col justify-between min-h-[200px] text-left overflow-hidden hover:shadow-card transition group disabled:opacity-50"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/40 rounded-full blur-2xl -translate-y-1/3 translate-x-1/3" />
          <div className="absolute bottom-0 left-0 w-28 h-28 bg-primary-500/20 rounded-full blur-2xl translate-y-1/3 -translate-x-1/3" />
          <div className="relative">
            <div className="w-8 h-8 rounded-sm bg-white/70 backdrop-blur flex items-center justify-center text-primary-700">
              <IconUser size={16} />
            </div>
          </div>
          <div className="relative">
            <div className="text-[15px] font-medium text-ink-900 leading-tight">
              Démarrer mon
              <br />
              identification
            </div>
            <div className="text-[11px] text-primary-800/70 mt-1 font-light">
              Parcours guidé en 8 étapes
            </div>
          </div>
        </button>

        <button
          onClick={() => onPick("/update")}
          disabled={disabled}
          className="relative bg-accent-100 hover:bg-accent-200/70 rounded-sm p-3.5 min-h-[95px] text-left transition group disabled:opacity-50"
        >
          <div className="w-7 h-7 rounded-sm bg-white/70 backdrop-blur flex items-center justify-center text-accent-700 mb-2">
            <IconFileText size={14} />
          </div>
          <div className="text-[13px] font-medium text-ink-900 leading-tight">
            Mettre à jour
          </div>
          <div className="text-[11px] text-ink-600 mt-0.5 font-light">
            mon dossier
          </div>
        </button>

        <button
          onClick={() => onPick("/status")}
          disabled={disabled}
          className="relative bg-primary-50 hover:bg-primary-100 rounded-sm p-3.5 min-h-[95px] text-left transition group disabled:opacity-50"
        >
          <div className="w-7 h-7 rounded-sm bg-white/80 backdrop-blur flex items-center justify-center text-primary-700 mb-2">
            <IconActivity size={14} />
          </div>
          <div className="text-[13px] font-medium text-ink-900 leading-tight">
            Mon statut
          </div>
          <div className="text-[11px] text-ink-600 mt-0.5 font-light">
            Vérifier mon dossier
          </div>
        </button>
      </div>

      <div className="mb-2">
        <div className="text-[11px] uppercase tracking-[0.12em] text-ink-400 font-medium mb-3">
          Aide rapide
        </div>
        <div className="space-y-1.5">
          {QUICK_TIPS.map((tip, i) => {
            const Icon = tip.icon;
            const tones = [
              "bg-primary-100 text-primary-700",
              "bg-accent-100 text-accent-700",
              "bg-primary-50 text-primary-700",
            ];
            return (
              <button
                key={i}
                onClick={() => onPick(tip.payload)}
                disabled={disabled}
                className="w-full flex items-center gap-3 text-left px-2 py-2 rounded-sm hover:bg-ink-50 transition group disabled:opacity-50"
              >
                <div className={`w-8 h-8 rounded-sm flex items-center justify-center shrink-0 ${tones[i % tones.length]}`}>
                  <Icon size={14} />
                </div>
                <span className="text-[13px] text-ink-700 font-normal group-hover:text-ink-900 transition leading-snug">
                  {tip.text}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const Transcript = ({
  messages,
  loading,
  avatarOk,
  bottomRef,
}: {
  messages: Message[];
  loading: boolean;
  avatarOk: boolean;
  bottomRef: React.RefObject<HTMLDivElement>;
}) => (
  <div className="flex-1 overflow-y-auto">
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-5">
      {messages.map((m: Message, idx: number) => (
        <MessageBubble key={m.id} message={m} previous={messages[idx - 1]} avatarOk={avatarOk} />
      ))}
      {loading && (
        <div className="flex items-start gap-2.5 animate-fade-in">
          <div className="w-9 h-9 rounded-full overflow-hidden ring-1 ring-ink-200 shrink-0 mt-1">
            <AssistantAvatar size={36} avatarOk={avatarOk} ring={false} />
          </div>
          <div className="bg-ink-100/80 rounded-[14px] rounded-tl-[4px] px-4 py-3">
            <Dots />
          </div>
        </div>
      )}
      <div ref={bottomRef} aria-hidden className="h-1" />
    </div>
  </div>
);

function MessageBubble({
  message,
  previous,
  avatarOk,
}: {
  message: Message;
  previous?: Message;
  avatarOk: boolean;
}) {
  const isOut = message.direction === "out";
  const sameAuthor = previous?.direction === message.direction;
  const time = new Date(message.timestamp).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (isOut) {
    return (
      <div className="flex items-start gap-2.5 animate-slide-up">
        {!sameAuthor ? (
          <div className="w-9 h-9 rounded-full overflow-hidden ring-1 ring-ink-200 shrink-0 mt-1">
            <AssistantAvatar size={36} avatarOk={avatarOk} ring={false} />
          </div>
        ) : (
          <div className="w-9 shrink-0" />
        )}
        <div className="bg-ink-100/80 rounded-[14px] rounded-tl-[4px] px-4 py-3 max-w-[88%] sm:max-w-[80%]">
          {!sameAuthor && (
            <div className="text-[13px] font-semibold text-ink-900 mb-0.5">MA2E Assistant</div>
          )}
          <div className="text-[14px] font-normal text-ink-800 leading-[1.6] whitespace-pre-wrap">
            {renderText(message.text)}
          </div>
          <div className="text-[10.5px] text-ink-400 text-right mt-1.5 inline-flex items-center gap-1 w-full justify-end">
            {time}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5 justify-end animate-slide-up">
      <div className="bg-primary-500 text-white rounded-[14px] rounded-tr-[4px] px-4 py-3 max-w-[80%] sm:max-w-[70%] shadow-sm">
        <div className="text-[14px] font-normal leading-[1.6] whitespace-pre-wrap">
          {renderText(message.text)}
        </div>
        <div className="text-[10.5px] text-white/75 text-right mt-1.5 inline-flex items-center gap-1 w-full justify-end">
          {time}
          <DoubleCheck tone="light" />
        </div>
      </div>
    </div>
  );
}

function DoubleCheck({ tone = "dark" }: { tone?: "dark" | "light" }) {
  const color = tone === "light" ? "rgba(255,255,255,0.85)" : "#64748B";
  return (
    <svg width="14" height="10" viewBox="0 0 16 11" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
      <path
        d="M1 5L4.5 8.5L10.5 1.5"
        stroke={color}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M5.5 5L9 8.5L14.5 1.5"
        stroke={color}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function renderText(text: string) {
  const html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*(.+?)\*/g, '<strong class="font-medium">$1</strong>')
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="bg-black/10 px-1.5 py-0.5 rounded-sm text-[13px] font-mono">$1</code>')
    .replace(/\n/g, "<br/>");
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function Dots() {
  return (
    <span className="inline-flex gap-1 items-center">
      <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
      <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
      <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
    </span>
  );
}
