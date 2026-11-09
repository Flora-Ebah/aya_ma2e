export type ChatFieldOption = { code: string; label: string };
export type ChatFormField = {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  placeholder?: string;
  options?: ChatFieldOption[];
  allow_other?: boolean;
  default?: string;
};
export type ChatUiHint =
  | {
      type: "form";
      title?: string;
      description?: string;
      fields: ChatFormField[];
    }
  | {
      type: "select";
      name: string;
      label: string;
      description?: string;
      options: ChatFieldOption[];
      allow_other?: boolean;
    }
  | {
      type: "signature";
      title?: string;
      description?: string;
    }
  | {
      type: "multi-select";
      name: string;
      title?: string;
      description?: string;
      options: ChatFieldOption[];
      min?: number;
      max?: number;
    };

export type ChatMessage = {
  id: string;
  direction: "in" | "out";
  text: string;
  timestamp: number;
  ui?: ChatUiHint | null;
  /** Vrai quand l'utilisateur a déjà répondu à ce formulaire (lock). */
  uiAnswered?: boolean;
};

export type PendingFile = {
  name: string;
  size: number;
  type: string;
  url?: string;
  uploading: boolean;
};

export const SESSION_KEY = "ma2e_chat_session";
export const TENANT_SLUG = "ma2e";

export function uuid(): string {
  return crypto.randomUUID
    ? crypto.randomUUID()
    : `web-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

export function greeting(hour: number): string {
  if (hour >= 5 && hour < 12) return "Bonjour";
  if (hour >= 12 && hour < 18) return "Bon après-midi";
  return "Bonsoir";
}

/** Rendu Markdown minimal (bold *…*, italic _…_, code `…`, retours ligne). */
export function renderText(text: string) {
  const html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*(.+?)\*/g, '<strong class="sa-strong">$1</strong>')
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="chat-code">$1</code>')
    .replace(/\n/g, "<br/>");
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}
