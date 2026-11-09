import { cloneElement, isValidElement } from "react";
import type { ReactElement, ReactNode } from "react";

type Props = {
  /** Texte de l'infobulle (court). */
  content: string;
  position?: "top" | "bottom" | "left" | "right";
  /** Un seul élément focusable : il reçoit `data-tooltip` (affiché au survol ET au focus clavier). */
  children: ReactNode;
};

/**
 * Infobulle CSS (`data-tooltip`). Ne remplace pas le libellé accessible :
 * un bouton icône garde son `aria-label`.
 *   <Tooltip content="Copier"><IconButton icon="copy-01" label="Copier" /></Tooltip>
 */
export function Tooltip({ content, position = "top", children }: Props) {
  if (isValidElement(children)) {
    return cloneElement(children as ReactElement<Record<string, unknown>>, { "data-tooltip": content, "data-tooltip-pos": position });
  }
  return (
    <span data-tooltip={content} data-tooltip-pos={position} tabIndex={0}>
      {children}
    </span>
  );
}
