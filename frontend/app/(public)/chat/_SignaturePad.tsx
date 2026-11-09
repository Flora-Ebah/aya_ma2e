"use client";
import { useEffect, useRef, useState } from "react";
import { TENANT_SLUG } from "./_utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Props = {
  sessionId: string;
  title?: string;
  description?: string;
  disabled?: boolean;
  onSubmit: (mediaUrl: string, displayText: string) => void;
  onEscape?: () => void;
};

type Mode = "draw" | "upload";

/**
 * Deux modes au choix pour une étape « signature » :
 *   - DRAW  : canvas tactile/souris, exportée en PNG → upload.
 *   - UPLOAD: fichier image (JPEG/PNG) → upload direct.
 *
 * Dans les deux cas, on POST l'image vers `/webhooks/web/upload/{slug}` et on
 * renvoie l'URL de media à `onSubmit` pour que le dispatcher l'enregistre
 * comme tour conversationnel avec `media_url`.
 */
export default function SignaturePad({
  sessionId, title, description, disabled, onSubmit, onEscape,
}: Props) {
  const [mode, setMode] = useState<Mode>("draw");
  const [hasInk, setHasInk] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // Haute résolution : backing store 2× pour un rendu net sur les écrans HiDPI.
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.scale(dpr, dpr);
      ctx.lineWidth = 2.2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#111827";
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, rect.width, rect.height);
    }
  }, [mode]);

  function getPoint(e: React.PointerEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function onPointerDown(e: React.PointerEvent<HTMLCanvasElement>) {
    if (disabled || sending) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
    drawingRef.current = true;
    const { x, y } = getPoint(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  function onPointerMove(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawingRef.current) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = getPoint(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    if (!hasInk) setHasInk(true);
  }

  function onPointerUp() {
    drawingRef.current = false;
  }

  function clearCanvas() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, rect.width, rect.height);
    setHasInk(false);
  }

  async function uploadBlob(blob: Blob, filename: string) {
    const fd = new FormData();
    fd.append("file", blob, filename);
    fd.append("session_id", sessionId);
    const res = await fetch(`${API_URL}/webhooks/web/upload/${TENANT_SLUG}`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error(await res.text() || "Échec de l'envoi");
    const data = await res.json();
    return data.media_url as string;
  }

  async function submitDrawing() {
    const canvas = canvasRef.current;
    if (!canvas || !hasInk || sending) return;
    setSending(true);
    setError(null);
    try {
      const blob: Blob = await new Promise((resolve, reject) =>
        canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("export impossible"))), "image/png"),
      );
      const url = await uploadBlob(blob, `signature-${Date.now()}.png`);
      onSubmit(url, "✍️ Signature manuscrite envoyée");
    } catch (e: any) {
      setError(e?.message || "Erreur d'envoi");
    } finally {
      setSending(false);
    }
  }

  async function onFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || sending) return;
    if (!/^image\//.test(file.type)) {
      setError("Le fichier doit être une image.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 5 Mo).");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const url = await uploadBlob(file, file.name);
      onSubmit(url, `✍️ Signature envoyée (${file.name})`);
    } catch (err: any) {
      setError(err?.message || "Erreur d'envoi");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-sig chat-formcard">
      {title && <div className="chat-formcard__title">{title}</div>}
      {description && <div className="chat-formcard__desc">{description}</div>}
      <div className="chat-sig__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "draw"}
          className={`chat-sig__tab${mode === "draw" ? " is-active" : ""}`}
          onClick={() => setMode("draw")}
          disabled={disabled || sending}
        >
          Signer ici
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "upload"}
          className={`chat-sig__tab${mode === "upload" ? " is-active" : ""}`}
          onClick={() => setMode("upload")}
          disabled={disabled || sending}
        >
          Importer une image
        </button>
      </div>

      {mode === "draw" ? (
        <>
          <div className="chat-sig__canvas-wrap">
            <canvas
              ref={canvasRef}
              className="chat-sig__canvas"
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
              onPointerLeave={onPointerUp}
              style={{ touchAction: "none" }}
            />
          </div>
          <div className="chat-sig__actions">
            <button
              type="button"
              className="sa-btn sa-btn--ghost"
              onClick={clearCanvas}
              disabled={!hasInk || sending}
            >
              Effacer
            </button>
            <button
              type="button"
              className="sa-btn sa-btn--primary"
              onClick={submitDrawing}
              disabled={!hasInk || sending}
            >
              {sending ? "Envoi…" : "Valider la signature"}
            </button>
          </div>
        </>
      ) : (
        <div className="chat-sig__upload">
          <label className="sa-btn sa-btn--primary" style={{ cursor: "pointer" }}>
            {sending ? "Envoi…" : "Choisir une image"}
            <input
              type="file"
              accept="image/*"
              onChange={onFilePick}
              disabled={disabled || sending}
              style={{ display: "none" }}
            />
          </label>
          <span className="chat-sig__hint">JPEG ou PNG, max 5 Mo.</span>
        </div>
      )}

      {error && <div className="chat-form__err">{error}</div>}

      {onEscape && (
        <button
          type="button"
          className="chat-formcard__escape"
          onClick={onEscape}
          disabled={disabled || sending}
        >
          Annuler et recommencer
        </button>
      )}
    </div>
  );
}
