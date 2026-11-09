"use client";
import type { ReactNode } from "react";
import { Drawer as KitDrawer } from "@/components/ui";
import "./assistante.css";

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  /** Largeur : "wide" 640 px, "xl" 960 px, "full" plein écran (tiroir du kit). */
  size?: "wide" | "xl" | "full";
};

/** Tiroir : panneau latéral (édition d'étape, création) ou plein écran (simulateur). */
export default function Drawer({ open, onClose, title, children, footer, size }: Props) {
  if (size === "full") {
    return (
      <KitDrawer open={open} onClose={onClose} title={title} variant="fullscreen">
        <div className="sa-stack">{children}</div>
      </KitDrawer>
    );
  }
  return (
    <KitDrawer
      open={open} onClose={onClose} title={title} variant="side" footer={footer}
      className={size === "xl" ? "ass-drawer-xl" : size === "wide" ? "sa-drawer--wide" : undefined}
    >
      {children}
    </KitDrawer>
  );
}
