"use client";
import { useEffect, useRef, useState } from "react";
import { SESSION_KEY, TENANT_SLUG, uuid, type ChatMessage, type PendingFile } from "./_utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Session chat public (visiteur) : messages + upload + envoi webhook web. */
export function useChatSession() {
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<PendingFile | null>(null);
  const bootRef = useRef(false);

  useEffect(() => {
    if (bootRef.current) return;
    bootRef.current = true;
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = uuid();
      localStorage.setItem(SESSION_KEY, sid);
    }
    setSessionId(sid);
  }, []);

  async function send(message: string, mediaUrl?: string, displayOverride?: string) {
    if (!sessionId) return;
    if (!message.trim() && !mediaUrl) return;
    setError(null);
    setLoading(true);

    const displayText =
      displayOverride ||
      (mediaUrl
        ? message || `Pièce jointe : ${pendingFile?.name || "fichier"}`
        : message);

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
        {
          id: uuid(),
          direction: "out",
          text: data.reply,
          timestamp: Date.now(),
          ui: data.ui ?? null,
        },
      ]);
    } catch (e: any) {
      setError(e.message || "Erreur de communication");
    } finally {
      setLoading(false);
    }
  }

  async function uploadFile(file: File) {
    if (!sessionId) return;
    // Garde-fou côté client : évite d'envoyer un fichier qu'on sait trop gros.
    // Backend accepte 5 Mo (F-01), Nginx 20 Mo — on prend 5 pour matcher la règle métier.
    const MAX_BYTES = 5 * 1024 * 1024;
    if (file.size > MAX_BYTES) {
      const mb = (file.size / 1024 / 1024).toFixed(1);
      setError(`📎 Fichier trop volumineux (${mb} Mo). Taille maximale : 5 Mo. Réduis ou re-prends la photo en qualité moyenne.`);
      return;
    }
    setPendingFile({ name: file.name, size: file.size, type: file.type, uploading: true });
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("session_id", sessionId);
      const res = await fetch(`${API_URL}/webhooks/web/upload/${TENANT_SLUG}`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        // Mapping HTTP → messages lisibles (pas de HTML Nginx brut dans l'UI).
        let msg: string;
        if (res.status === 413) {
          msg = "📎 Fichier trop volumineux. Taille maximale : 5 Mo.";
        } else if (res.status === 415) {
          msg = "📎 Format non supporté. Utilise une image JPEG, PNG, HEIC ou WebP.";
        } else if (res.status === 401 || res.status === 403) {
          msg = "📎 Session expirée. Rafraîchis la page et recommence.";
        } else if (res.status >= 500) {
          msg = "📎 Problème serveur lors de l'envoi. Réessaie dans un instant.";
        } else {
          // Essai parsing JSON {detail: "..."} FastAPI ; fallback générique.
          try {
            const body = await res.json();
            msg = body?.detail ? `📎 ${body.detail}` : `📎 Échec de l'envoi (HTTP ${res.status}).`;
          } catch {
            msg = `📎 Échec de l'envoi (HTTP ${res.status}).`;
          }
        }
        setError(msg);
        setPendingFile(null);
        return;
      }
      const data = await res.json();
      setPendingFile({
        name: file.name, size: file.size, type: file.type,
        url: data.media_url, uploading: false,
      });
    } catch (e: any) {
      setError("📎 Connexion interrompue. Vérifie ton réseau et réessaie.");
      setPendingFile(null);
    }
  }

  function markUiAnswered(messageId: string) {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, uiAnswered: true } : m)),
    );
  }

  function reset() {
    localStorage.removeItem(SESSION_KEY);
    setMessages([]);
    const sid = uuid();
    localStorage.setItem(SESSION_KEY, sid);
    setSessionId(sid);
  }

  return {
    sessionId, messages, loading, error,
    pendingFile, setPendingFile,
    send, uploadFile, reset,
    markUiAnswered,
    setError,
  };
}
