"use client";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

/** Pile des dialogues ouverts : un seul est actif, les précédents sont `inert`. */
const stack: HTMLDialogElement[] = [];

/** `useLayoutEffect` sûr côté serveur. */
export const useIsoLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

/** Vrai une fois monté côté client (pour les portails). */
export function useMounted() {
  const [m, setM] = useState(false);
  useEffect(() => setM(true), []);
  return m;
}

/**
 * Pilote un `<dialog>` natif : `showModal()` à l'ouverture (focus piégé, Échap,
 * backdrop), pile unique (les dialogues du dessous deviennent inertes), focus
 * rendu au déclencheur à la fermeture.
 */
export function useModalDialog(opts: { onClose: () => void; initialFocus?: "first-field" | "none" }) {
  const ref = useRef<HTMLDialogElement>(null);
  const onCloseRef = useRef(opts.onClose);
  onCloseRef.current = opts.onClose;
  const initial = opts.initialFocus ?? "first-field";

  useIsoLayoutEffect(() => {
    const d = ref.current;
    if (!d) return;
    const trigger = document.activeElement as HTMLElement | null;
    stack.forEach((x) => x.setAttribute("inert", ""));
    stack.push(d);
    if (!d.open) d.showModal();

    if (initial === "first-field") {
      const first = d.querySelector<HTMLElement>("input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])");
      const lastBtn = d.querySelector<HTMLElement>("[data-dialog-footer] button:last-child, .sa-dialog__footer button:last-child, .sa-tiroir__actions button:last-child");
      (first ?? lastBtn)?.focus();
    }

    const onCancel = (e: Event) => {
      e.preventDefault();
      onCloseRef.current();
    };
    d.addEventListener("cancel", onCancel);
    return () => {
      d.removeEventListener("cancel", onCancel);
      const i = stack.indexOf(d);
      if (i >= 0) stack.splice(i, 1);
      stack[stack.length - 1]?.removeAttribute("inert");
      if (d.open) d.close();
      if (trigger?.isConnected && stack.length === 0) trigger.focus?.({ preventScroll: true });
    };
  }, [initial]);

  return ref;
}
