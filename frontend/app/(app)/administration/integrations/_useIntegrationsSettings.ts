"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import { coerceSettingValue, type SettingValue } from "@/components/settings/SettingRow";

/** Charge, groupe et met à jour les settings de la catégorie « integrations ». */
export function useIntegrationsSettings() {
  const toast = useToast();
  const [settings, setSettings] = useState<SettingValue[]>([]);
  const [drafts, setDrafts] = useState<Record<string, any>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { void load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await api.getSettingsCategory("integrations");
      setSettings(data.settings);
      const d: Record<string, any> = {};
      data.settings.forEach((s: SettingValue) => (d[s.key] = s.value));
      setDrafts(d);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  function setDraft(key: string, value: any) {
    setDrafts((prev) => ({ ...prev, [key]: value }));
  }

  function hasChange(s: SettingValue): boolean {
    const draft = drafts[s.key];
    if (draft === undefined || draft === null) return false;
    return draft !== s.value;
  }

  async function save(s: SettingValue) {
    if (!hasChange(s)) return;
    setSavingKey(s.key);
    try {
      const value = coerceSettingValue(drafts[s.key], s.value_type);
      await api.updateSetting("integrations", s.key, value);
      toast({ tone: "success", title: "Enregistré", message: s.label });
      await load();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setSavingKey(null);
    }
  }

  const byGroup: Record<string, SettingValue[]> = {};
  settings.forEach((s) => {
    const g = s.group || "Général";
    (byGroup[g] = byGroup[g] || []).push(s);
  });

  return { loading, byGroup, drafts, savingKey, setDraft, hasChange, save };
}
