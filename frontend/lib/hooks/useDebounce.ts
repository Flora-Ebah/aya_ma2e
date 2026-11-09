"use client";
import { useEffect, useState } from "react";

/**
 * Debounce une valeur — utile pour les champs de recherche qui doivent
 * attendre que l'utilisateur ait fini de taper avant de déclencher un fetch.
 *
 * @example
 *   const [q, setQ] = useState("");
 *   const debouncedQ = useDebounce(q, 300);
 *   useEffect(() => { void search(debouncedQ); }, [debouncedQ]);
 */
export function useDebounce<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}
