"use client";
import { useCallback, useEffect, useRef, useState } from "react";

type State<T> = {
  /** Données renvoyées par l'API (null tant qu'aucun fetch réussi). */
  data: T | null;
  /** true pendant qu'une requête est en cours. */
  loading: boolean;
  /** Message d'erreur (null si tout va bien). */
  error: string | null;
};

type Options = {
  /** Si false, ne lance pas le fetch au montage (utile si on attend un param). */
  auto?: boolean;
};

/**
 * Hook générique pour appeler une fonction async, gérer loading/error/data
 * et exposer un `refetch()`. Remplace le pattern répété sur ~15 pages :
 *
 *   const [data, setData] = useState(null);
 *   const [loading, setLoading] = useState(true);
 *   const [error, setError] = useState(null);
 *
 *   useEffect(() => { load(); }, []);
 *   async function load() {
 *     setLoading(true);
 *     try { setData(await api.xxx()); }
 *     catch (e) { setError(e.message); }
 *     finally { setLoading(false); }
 *   }
 *
 * @example
 *   const { data, loading, error, refetch } = useApi(
 *     () => api.listDossiers({ status: "valide" }),
 *   );
 *
 *   const { refetch: create } = useApi(
 *     (payload) => api.createRole(payload),
 *     { auto: false },
 *   );
 */
export function useApi<T>(fetcher: () => Promise<T>, opts: Options = {}) {
  const { auto = true } = opts;
  const [state, setState] = useState<State<T>>({ data: null, loading: auto, error: null });
  const cancelled = useRef(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcherRef.current();
      if (!cancelled.current) setState({ data, loading: false, error: null });
    } catch (e: any) {
      if (!cancelled.current) {
        setState((s) => ({ ...s, loading: false, error: e?.message || "Erreur inconnue" }));
      }
    }
  }, []);

  useEffect(() => {
    cancelled.current = false;
    if (auto) void run();
    return () => {
      cancelled.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    ...state,
    /** Relance la requête manuellement (bouton Actualiser, après create/update/delete…). */
    refetch: run,
    /** Écrase les données localement (optimistic update). */
    setData: (data: T | null) => setState((s) => ({ ...s, data })),
  };
}
