"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { Modal } from "@/components/ui/Modal";

type ConfirmVariant = "default" | "danger" | "success";

type ConfirmOptions = {
  title?: string;
  message?: string | React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  icon?: "warn" | "danger" | "success" | "info" | null;
};

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;

type Toast = {
  id: string;
  tone: "success" | "error" | "info" | "warning";
  title?: string;
  message: string;
};

type ToastFn = (toast: Omit<Toast, "id">) => void;

const ConfirmContext = createContext<{ confirm: ConfirmFn; toast: ToastFn } | null>(null);

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx.confirm;
}

export function useToast() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useToast must be used within ConfirmProvider");
  return ctx.toast;
}

const MAX_TOASTS = 3;

/**
 * Fournisseur global : confirmations (modale `sa-dialog--sm`, promesse booléenne)
 * et toasts (`sa-toast`, région en bas à droite, 3 max, `aria-live`).
 * API inchangée : `useConfirm()` et `useToast()`.
 */
export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState<{
    options: ConfirmOptions;
    resolve: (v: boolean) => void;
  } | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => setPending({ options, resolve }));
  }, []);

  const dismiss = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t) clearTimeout(t);
    timers.current.delete(id);
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const toast = useCallback(
    (t: Omit<Toast, "id">) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev, { ...t, id }].slice(-MAX_TOASTS));
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), t.tone === "error" ? 7000 : 4500),
      );
    },
    [dismiss],
  );

  function close(result: boolean) {
    if (pending) {
      pending.resolve(result);
      setPending(null);
    }
  }

  useEffect(() => {
    if (!pending) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Enter" && !(e.target instanceof HTMLButtonElement)) close(true);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  const o = pending?.options;
  const variant = o?.variant ?? "default";
  const iconName =
    o?.icon === null
      ? undefined
      : o?.icon === "danger"
        ? "alert-circle"
        : o?.icon === "success"
          ? "checkmark-circle-02"
          : o?.icon === "info"
            ? "information-circle"
            : "alert-02";

  return (
    <ConfirmContext.Provider value={{ confirm, toast }}>
      {children}
      <Modal
        open={Boolean(pending)}
        onClose={() => close(false)}
        title={o?.title ?? "Confirmation"}
        icon={iconName}
        danger={variant === "danger"}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => close(false)}>
              {o?.cancelText || "Annuler"}
            </Button>
            <Button variant={variant === "danger" ? "danger" : "primary"} onClick={() => close(true)} autoFocus>
              {o?.confirmText || "Confirmer"}
            </Button>
          </>
        }
      >
        {o?.message && <div className="sa-body">{o.message}</div>}
      </Modal>
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ConfirmContext.Provider>
  );
}

const TOAST_ICON: Record<Toast["tone"], string> = {
  success: "checkmark-circle-02",
  error: "alert-circle",
  warning: "alert-02",
  info: "information-circle",
};

function ToastStack({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div className="sa-toast-region" aria-live="polite" aria-atomic="false">
      {toasts.map((t) => (
        <div key={t.id} className={`sa-toast sa-toast--${t.tone}`} role={t.tone === "error" ? "alert" : "status"}>
          <Icon name={TOAST_ICON[t.tone]} />
          <div className="sa-toast__body">
            {t.title && <div className="sa-toast__title">{t.title}</div>}
            <div className="sa-toast__text">{t.message}</div>
          </div>
          <IconButton icon="cancel-01" label="Fermer la notification" tooltip={false} onClick={() => onDismiss(t.id)} />
        </div>
      ))}
    </div>
  );
}
