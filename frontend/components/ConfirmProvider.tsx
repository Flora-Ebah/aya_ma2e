"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { IconAlertCircle, IconCheck, IconShield, IconX } from "@/components/icons";

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
  tone: "success" | "error" | "info";
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

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState<{
    options: ConfirmOptions;
    resolve: (v: boolean) => void;
  } | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => setPending({ options, resolve }));
  }, []);

  const toast = useCallback((t: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 4000);
  }, []);

  function close(result: boolean) {
    if (pending) {
      pending.resolve(result);
      setPending(null);
    }
  }

  useEffect(() => {
    if (!pending) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close(false);
      if (e.key === "Enter") close(true);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pending]);

  return (
    <ConfirmContext.Provider value={{ confirm, toast }}>
      {children}
      {pending && (
        <ConfirmDialog
          {...pending.options}
          onConfirm={() => close(true)}
          onCancel={() => close(false)}
        />
      )}
      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((p) => p.filter((x) => x.id !== id))} />
    </ConfirmContext.Provider>
  );
}

function ConfirmDialog({
  title,
  message,
  confirmText,
  cancelText,
  variant = "default",
  icon = "warn",
  onConfirm,
  onCancel,
}: ConfirmOptions & { onConfirm: () => void; onCancel: () => void }) {
  const iconTone =
    variant === "danger"
      ? "bg-red-50 text-red-600"
      : variant === "success"
        ? "bg-primary-50 text-primary-600"
        : "bg-accent-50 text-accent-600";

  const IconCmp =
    icon === "danger"
      ? IconX
      : icon === "success"
        ? IconCheck
        : icon === "info"
          ? IconShield
          : IconAlertCircle;

  const confirmBtn =
    variant === "danger"
      ? "btn-danger"
      : variant === "success"
        ? "btn-success"
        : "btn-primary";

  return (
    <div
      className="fixed inset-0 bg-ink-900/40 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-fade-in"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded shadow-floating w-full max-w-md p-5 animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex gap-3">
          {icon && (
            <div className={`w-10 h-10 rounded-sm flex items-center justify-center shrink-0 ${iconTone}`}>
              <IconCmp size={20} />
            </div>
          )}
          <div className="flex-1 min-w-0 pt-0.5">
            {title && <h3 className="text-[15px] font-semibold text-ink-900 leading-tight">{title}</h3>}
            {message && (
              <div className="text-[13.5px] text-ink-600 leading-relaxed mt-1.5 font-light">
                {message}
              </div>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onCancel} className="btn-secondary">
            {cancelText || "Annuler"}
          </button>
          <button onClick={onConfirm} className={confirmBtn} autoFocus>
            {confirmText || "Confirmer"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed top-4 right-4 z-[110] space-y-2 max-w-sm w-full">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const config = {
    success: { bg: "bg-primary-50 border-primary-200", icon: "text-primary-600", Icon: IconCheck },
    error: { bg: "bg-red-50 border-red-200", icon: "text-red-600", Icon: IconAlertCircle },
    info: { bg: "bg-accent-50 border-accent-200", icon: "text-accent-700", Icon: IconShield },
  }[toast.tone];
  const Icon = config.Icon;
  return (
    <div className={`${config.bg} border rounded shadow-card p-3 pr-2 flex items-start gap-2.5 animate-slide-up`}>
      <Icon size={18} className={`${config.icon} shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        {toast.title && (
          <div className="text-[13px] font-medium text-ink-900 leading-tight">{toast.title}</div>
        )}
        <div className="text-[12.5px] text-ink-700 mt-0.5 leading-snug">{toast.message}</div>
      </div>
      <button
        onClick={onDismiss}
        className="text-ink-400 hover:text-ink-700 p-1 -m-1 rounded-sm transition"
      >
        <IconX size={14} />
      </button>
    </div>
  );
}
