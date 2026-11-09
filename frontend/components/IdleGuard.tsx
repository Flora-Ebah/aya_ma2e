"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api";

/**
 * Déconnecte automatiquement l'utilisateur après une période d'inactivité.
 * Réduit la fenêtre d'exposition en cas de poste laissé sans surveillance
 * (agent qui va en réunion en oubliant sa session).
 *
 * Un bandeau d'avertissement s'affiche 60 secondes avant la déconnexion,
 * permettant à l'utilisateur de rester connecté en cliquant / bougeant la
 * souris.
 */
const IDLE_TIMEOUT_MS = 20 * 60 * 1000; // 20 minutes total
const WARNING_BEFORE_MS = 60 * 1000; // avertissement 60s avant

const ACTIVITY_EVENTS = [
  "mousedown",
  "keydown",
  "touchstart",
  "scroll",
] as const;

export default function IdleGuard() {
  const router = useRouter();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const clearAll = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (warningRef.current) clearTimeout(warningRef.current);
    };

    const doLogout = async () => {
      clearAll();
      await logout();
      router.replace("/login?expired=1");
    };

    const reset = () => {
      clearAll();
      setShowWarning(false);
      warningRef.current = setTimeout(() => {
        setShowWarning(true);
      }, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);
      timerRef.current = setTimeout(doLogout, IDLE_TIMEOUT_MS);
    };

    ACTIVITY_EVENTS.forEach((evt) => window.addEventListener(evt, reset, { passive: true }));
    reset();

    return () => {
      clearAll();
      ACTIVITY_EVENTS.forEach((evt) => window.removeEventListener(evt, reset));
    };
  }, [router]);

  if (!showWarning) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-xs bg-white border border-amber-300 shadow-card rounded-sm p-3">
      <div className="text-[11px] font-semibold text-amber-700 uppercase tracking-wide mb-1">
        Session bientôt expirée
      </div>
      <div className="text-[12px] text-ink-700 leading-snug">
        Aucune activité détectée depuis 19 minutes. Vous serez déconnecté(e) dans
        moins de 60 secondes. Bougez la souris pour rester connecté(e).
      </div>
    </div>
  );
}
