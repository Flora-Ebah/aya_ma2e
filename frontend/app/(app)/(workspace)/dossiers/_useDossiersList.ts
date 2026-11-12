"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AdvancedFilters, Dossier, Stats } from "./_types";

export type ListParams = {
  /** Recherche (envoyée au serveur) */
  q: string;
  /** "" = toutes | "import" = base MA2E importée | "inscription" = chatbot */
  origine: string;
  page: number;
  pageSize: number;
};

/**
 * Charge UNE page de dossiers + stats avec filtres. La pagination, la recherche et le total
 * sont calculés par le serveur : la liste peut contenir des milliers de sociétaires importés.
 * Fournit reload() pour rafraîchir.
 */
export function useDossiersList(statusFilter: string, advanced: AdvancedFilters, p: ListParams) {
  const [dossiers, setDossiers] = useState<Dossier[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [resp, s] = await Promise.all([
        api.listDossiers({
          status: statusFilter || undefined,
          employeur_code: advanced.employeur_code || undefined,
          agent_id: advanced.agent_id || undefined,
          priority_only: advanced.priority_only || undefined,
          overdue_only: advanced.overdue_only || undefined,
          since: advanced.since || undefined,
          until: advanced.until || undefined,
          sort: advanced.sort && advanced.sort !== "oldest_first" ? advanced.sort : undefined,
          q: p.q || undefined,
          origine: p.origine || undefined,
          limit: p.pageSize,
          offset: (p.page - 1) * p.pageSize,
        }),
        api.getStats(),
      ]);
      setDossiers(resp.items ?? resp);
      setTotal(resp.total ?? (resp.items ?? resp).length);
      setStats(s);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, advanced, p.q, p.origine, p.page, p.pageSize]);

  useEffect(() => { void load(); }, [load]);

  return { dossiers, total, stats, loading, error, reload: load };
}
