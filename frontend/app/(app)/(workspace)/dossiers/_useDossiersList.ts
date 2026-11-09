"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AdvancedFilters, Dossier, Stats } from "./_types";

/** Charge dossiers + stats avec filtres. Fournit reload() pour rafraîchir. */
export function useDossiersList(statusFilter: string, advanced: AdvancedFilters) {
  const [dossiers, setDossiers] = useState<Dossier[]>([]);
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
          limit: 500,
        }),
        api.getStats(),
      ]);
      setDossiers(resp.items ?? resp);
      setStats(s);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, advanced]);

  useEffect(() => { void load(); }, [load]);

  return { dossiers, stats, loading, error, reload: load };
}
