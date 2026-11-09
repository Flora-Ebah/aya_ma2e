"use client";
import { useCallback, useEffect, useState } from "react";

/** Préférence de thème : mémorisée dans le navigateur uniquement. */
export type ThemePref = "light" | "dark" | "system";
const KEY = "ma2e-theme";

export function readThemePref(): ThemePref {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    /* stockage indisponible (navigation privée stricte) */
  }
  return "system";
}

function resolve(pref: ThemePref): "light" | "dark" {
  if (pref !== "system") return pref;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Applique le thème sur <html> (data-theme) et mémorise la préférence. */
export function applyTheme(pref: ThemePref) {
  document.documentElement.setAttribute("data-theme", resolve(pref));
  document.documentElement.setAttribute("data-theme-pref", pref);
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    /* préférence non mémorisée */
  }
}

/** Hook : `[pref, setPref]`. Suit le thème du système tant que la préférence est « system ». */
export function useThemePref(): [ThemePref, (p: ThemePref) => void] {
  const [pref, setPrefState] = useState<ThemePref>("system");

  useEffect(() => {
    setPrefState(readThemePref());
  }, []);

  useEffect(() => {
    if (pref !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = () => applyTheme("system");
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [pref]);

  const setPref = useCallback((p: ThemePref) => {
    setPrefState(p);
    applyTheme(p);
  }, []);

  return [pref, setPref];
}
