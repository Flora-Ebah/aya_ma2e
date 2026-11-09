"use client";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { CSSProperties, ReactNode, RefObject } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/components/Icon";
import Link from "next/link";
import { IconButton } from "./IconButton";
import { cx } from "./util";

/* -------------------------------------------------------------------------- */
/* Popover : panneau flottant ancré à un déclencheur (portail, `position:fixed`) */
/* -------------------------------------------------------------------------- */

type TriggerProps = {
  ref: RefObject<HTMLButtonElement>;
  onClick: () => void;
  "aria-haspopup": "menu" | "dialog";
  "aria-expanded": boolean;
  "aria-controls": string | undefined;
};

type PopoverProps = {
  /** Rendu du déclencheur : reçoit les props à étaler sur le bouton. */
  trigger: (p: TriggerProps & { open: boolean }) => ReactNode;
  /** Contenu du panneau ; reçoit `close`. */
  children: (api: { close: () => void }) => ReactNode;
  align?: "start" | "end";
  /** Largeur du panneau (px). Défaut : celle de `.sa-menu` (280). */
  width?: number;
  role?: "menu" | "dialog";
  label?: string;
  panelClassName?: string;
  onOpenChange?: (open: boolean) => void;
};

/**
 * Popover générique : portail + `position: fixed` (jamais coupé par un
 * conteneur `overflow`), repositionné au défilement/redimensionnement,
 * s'ouvre vers le haut s'il manque de place, ferme sur Échap / clic extérieur.
 */
export function Popover({ trigger, children, align = "end", width, role = "dialog", label, panelClassName, onOpenChange }: PopoverProps) {
  const [open, setOpenState] = useState(false);
  const [style, setStyle] = useState<CSSProperties>({});
  const btnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const id = useId();

  const setOpen = useCallback(
    (v: boolean) => {
      setOpenState(v);
      onOpenChange?.(v);
    },
    [onOpenChange],
  );
  const close = useCallback(() => {
    setOpen(false);
    btnRef.current?.focus({ preventScroll: true });
  }, [setOpen]);

  const place = useCallback(() => {
    const b = btnRef.current;
    const p = panelRef.current;
    if (!b) return;
    const r = b.getBoundingClientRect();
    const w = width ?? p?.offsetWidth ?? 280;
    const h = p?.offsetHeight ?? 0;
    const margin = 8;
    let left = align === "end" ? r.right - w : r.left;
    left = Math.max(margin, Math.min(left, window.innerWidth - w - margin));
    let top = r.bottom + 8;
    if (h && top + h > window.innerHeight - margin && r.top - 8 - h > margin) top = r.top - 8 - h;
    setStyle({ position: "fixed", left, top, right: "auto", width: width ?? undefined, maxHeight: `calc(100dvh - ${margin * 2}px)`, overflowY: "auto" });
  }, [align, width]);

  useEffect(() => {
    if (!open) return;
    place();
    const raf = requestAnimationFrame(place);
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node;
      if (panelRef.current?.contains(t) || btnRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, place, close, setOpen]);

  // Focus sur le premier élément du menu à l'ouverture
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      const el = panelRef.current?.querySelector<HTMLElement>('[role="menuitem"]:not([disabled]), input, select, button:not([disabled]), a[href]');
      el?.focus({ preventScroll: true });
    }, 0);
    return () => clearTimeout(t);
  }, [open]);

  return (
    <>
      {trigger({
        ref: btnRef,
        onClick: () => setOpen(!open),
        "aria-haspopup": role === "menu" ? "menu" : "dialog",
        "aria-expanded": open,
        "aria-controls": open ? id : undefined,
        open,
      })}
      {open &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            ref={panelRef}
            id={id}
            role={role}
            aria-label={label}
            className={cx("sa-menu", panelClassName)}
            style={{ ...style, zIndex: 400 }}
            onKeyDown={(e) => {
              if (role !== "menu") return;
              const items = Array.from(panelRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([disabled])') ?? []);
              const i = items.indexOf(document.activeElement as HTMLElement);
              if (e.key === "ArrowDown") {
                e.preventDefault();
                items[(i + 1) % items.length]?.focus();
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                items[(i - 1 + items.length) % items.length]?.focus();
              } else if (e.key === "Tab") {
                setOpen(false);
              }
            }}
          >
            {children({ close })}
          </div>,
          // Dans un <dialog> (modale / tiroir), le panneau doit vivre dans la couche supérieure.
          (btnRef.current?.closest("dialog") as HTMLElement | null) ?? document.body,
        )}
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* DropdownMenu : liste d'actions (menu « ⋯ »)                                  */
/* -------------------------------------------------------------------------- */

export type MenuItem =
  | { separator: true; key?: string }
  | {
      label: string;
      icon?: string;
      onClick?: () => void;
      href?: string;
      danger?: boolean;
      disabled?: boolean;
      key?: string;
      separator?: false;
    };

type DropdownProps = {
  items: MenuItem[];
  /** Libellé accessible du déclencheur (« Actions »). */
  label?: string;
  /** Icône du déclencheur (défaut `more-horizontal`). */
  icon?: string;
  align?: "start" | "end";
  width?: number;
  /** Déclencheur personnalisé (sinon IconButton ⋯). */
  trigger?: (p: TriggerProps & { open: boolean }) => ReactNode;
};

/**
 * Menu d'actions. Chaque entrée : `onClick` ou `href`, icône, `danger`.
 *   <DropdownMenu label="Actions" items={[{label:"Modifier",icon:"edit-02",onClick:edit},{separator:true},{label:"Supprimer",icon:"delete-02",danger:true,onClick:del}]} />
 */
export function DropdownMenu({ items, label = "Actions", icon = "more-horizontal", align = "end", width = 220, trigger }: DropdownProps) {
  return (
    <Popover
      role="menu"
      label={label}
      align={align}
      width={width}
      trigger={
        trigger ??
        (({ open, ...p }) => <IconButton icon={icon} label={label} aria-expanded={p["aria-expanded"]} aria-haspopup="menu" aria-controls={p["aria-controls"]} ref={p.ref} onClick={p.onClick} tooltip={false} data-open={open || undefined} />)
      }
    >
      {({ close }) => (
        <>
          {items.map((it, i) => {
            if ("separator" in it && it.separator) return <div key={it.key ?? `s${i}`} className="sa-menu__sep" role="separator" />;
            const m = it as Exclude<MenuItem, { separator: true }>;
            const cls = cx("sa-menu__item", m.danger && "sa-menu__item--danger");
            const content = (
              <>
                {m.icon && <Icon name={m.icon} />}
                {m.label}
              </>
            );
            if (m.href && !m.disabled) {
              return (
                <Link key={m.key ?? m.label} href={m.href} role="menuitem" className={cls} onClick={close}>
                  {content}
                </Link>
              );
            }
            return (
              <button
                key={m.key ?? m.label}
                type="button"
                role="menuitem"
                className={cls}
                disabled={m.disabled}
                onClick={() => {
                  close();
                  m.onClick?.();
                }}
              >
                {content}
              </button>
            );
          })}
        </>
      )}
    </Popover>
  );
}
