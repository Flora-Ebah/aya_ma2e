import { createElement } from "react";
import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";

/** Concatène des classes en ignorant les valeurs falsy. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** Accepte soit un nom d'icône du sprite ("plus-sign"), soit un élément React déjà prêt. */
export type IconProp = string | ReactNode;

export function renderIcon(icon: IconProp | undefined, size?: number): ReactNode {
  if (icon === undefined || icon === null || icon === false) return null;
  if (typeof icon === "string") return createElement(Icon, { name: icon, size });
  return icon;
}
