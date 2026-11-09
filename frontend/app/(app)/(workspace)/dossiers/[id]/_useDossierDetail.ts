"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TOC } from "./_constants";

/** Charge le dossier + presets de motifs de rejet, expose scroll-spy sur les sections. */
export function useDossierDetail(id: string) {
  const [dossier, setDossier] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rejectMotivePresets, setRejectMotivePresets] = useState<string[]>([]);
  const [activeSection, setActiveSection] = useState<string>("vue-ensemble");

  useEffect(() => {
    void load();
    // Motifs de rejet prédéfinis (settings.general.rejection_motives) — best-effort
    api.getSettingsCategory("general")
      .then((cat: any) => {
        const motives = (cat.settings || []).find((s: any) => s.key === "rejection_motives");
        if (motives && Array.isArray(motives.value)) setRejectMotivePresets(motives.value);
      })
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    if (!dossier) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 },
    );
    TOC.forEach(({ id: sectionId }) => {
      const el = document.getElementById(sectionId);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [dossier]);

  async function load() {
    setLoading(true);
    try {
      setDossier(await api.getDossier(id));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return { dossier, loading, error, rejectMotivePresets, activeSection, reload: load };
}
