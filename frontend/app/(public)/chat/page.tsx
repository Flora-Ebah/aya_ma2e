"use client";
import { useEffect, useRef, useState } from "react";
import { useConfirm } from "@/components/ConfirmProvider";
import ChatHeader from "./_ChatHeader";
import Composer from "./_Composer";
import Transcript from "./_Transcript";
import WelcomeScreen from "./_WelcomeScreen";
import { useChatSession } from "./_useChatSession";
import { greeting } from "./_utils";

export default function ChatPage() {
  const confirm = useConfirm();
  const {
    sessionId, messages, loading, error, pendingFile, setPendingFile,
    send, uploadFile, reset, setError, markUiAnswered,
  } = useChatSession();

  const [input, setInput] = useState("");
  const [avatarOk, setAvatarOk] = useState(true);
  const [now] = useState(() => new Date());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const img = new window.Image();
    img.src = "/assistant-avatar.png";
    img.onerror = () => setAvatarOk(false);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading, pendingFile?.url]);

  function onFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 5 Mo).");
      return;
    }
    void uploadFile(f);
    e.target.value = "";
  }

  function onSubmit() {
    if (loading) return;
    const text = input.trim();
    const mediaUrl = pendingFile?.url;
    if (!text && !mediaUrl) return;
    if (pendingFile?.uploading) return;
    setInput("");
    void send(text, mediaUrl);
    setPendingFile(null);
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
    reset();
  }

  const hasMessages = messages.length > 0;
  const lastOut = [...messages].reverse().find((m) => m.direction === "out");
  const awaitingForm = !!(lastOut && lastOut.ui && !lastOut.uiAnswered);

  return (
    <div className="chat-page">
      <main className="chat-main" id="contenu">
        {hasMessages && <ChatHeader avatarOk={avatarOk} onReset={resetSession} />}

        {!hasMessages ? (
          <div className="chat-welcome">
            <WelcomeScreen
              hello={greeting(now.getHours())}
              avatarOk={avatarOk}
              onPick={(payload, display) => void send(payload, undefined, display)}
              disabled={loading}
            />
          </div>
        ) : (
          <Transcript
            messages={messages}
            loading={loading}
            avatarOk={avatarOk}
            bottomRef={bottomRef}
            sessionId={sessionId}
            onFormSubmit={(messageId, payload, display) => {
              markUiAnswered(messageId);
              void send(payload, undefined, display);
            }}
            onFormSubmitMedia={(messageId, mediaUrl, display) => {
              markUiAnswered(messageId);
              void send("", mediaUrl, display);
            }}
            onFormEscape={(messageId) => {
              markUiAnswered(messageId);
              void send("RECOMMENCER", undefined, "Recommencer");
            }}
          />
        )}

        {!awaitingForm && (
          <Composer
            input={input}
            hasMessages={hasMessages}
            loading={loading}
            error={error}
            pendingFile={pendingFile}
            onInputChange={setInput}
            onSubmit={onSubmit}
            onFilePick={onFilePick}
            onPendingFileRemove={() => setPendingFile(null)}
          />
        )}
      </main>
    </div>
  );
}
