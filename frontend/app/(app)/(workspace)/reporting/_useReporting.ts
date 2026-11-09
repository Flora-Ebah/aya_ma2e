"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import type {
  AgentPerf, ChannelStat, Funnel, OcrQuality, Overview, RejectionReason, TimelinePoint,
} from "./_types";

/** Charge tous les jeux de données du dashboard reporting pour une période. */
export function useReporting(period: number) {
  const toast = useToast();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [channels, setChannels] = useState<ChannelStat[]>([]);
  const [reasons, setReasons] = useState<RejectionReason[]>([]);
  const [agents, setAgents] = useState<AgentPerf[]>([]);
  const [ocr, setOcr] = useState<OcrQuality | null>(null);
  const [funnel, setFunnel] = useState<Funnel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { void load(); }, [period]);

  async function load() {
    setLoading(true);
    try {
      const [ov, tl, ch, rj, ag, oc, fn] = await Promise.all([
        api.statsOverview(period),
        api.statsTimeline(period),
        api.statsByChannel(),
        api.statsRejectionReasons(10),
        api.statsAgentsPerformance(90, 5),
        api.statsOcrQuality(90),
        api.statsConversionFunnel(period),
      ]);
      setOverview(ov);
      setTimeline(tl);
      setChannels(ch);
      setReasons(rj);
      setAgents(ag);
      setOcr(oc);
      setFunnel(fn);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  return { loading, overview, timeline, channels, reasons, agents, ocr, funnel };
}
