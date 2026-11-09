"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import { Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { SettingRow, SettingsGroup, coerceSettingValue } from "@/components/settings/SettingRow";
import type { SettingValue } from "@/components/settings/SettingRow";

// Clés déplacées dans Pilotage du chatbot → Comportement.
// On les masque ici pour éviter la double édition.
const CHATBOT_KEYS = new Set([
  "assistant_name",
  "session_max_idle_days",
  "ocr_min_confidence_score",
  "agent_handoff_target_minutes",
  "use_dynamic_workflow",
  "otp_max_attempts",
  "otp_validity_minutes",
  "artci_page_url",
]);

export default function GeneralSettingsPage() {
  const toast = useToast();
  const [settings, setSettings] = useState<SettingValue[]>([]);
  const [drafts, setDrafts] = useState<Record<string, any>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { void load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await api.getSettingsCategory("general");
      const filtered = data.settings.filter((s: SettingValue) => !CHATBOT_KEYS.has(s.key));
      setSettings(filtered);
      const d: Record<string, any> = {};
      filtered.forEach((s: SettingValue) => (d[s.key] = s.value));
      setDrafts(d);
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setLoading(false);
    }
  }

  function hasChange(s: SettingValue): boolean {
    const draft = drafts[s.key];
    if (draft === undefined || draft === null) return false;
    if (typeof draft === "string" && typeof s.value === "string") {
      return draft.trim() !== (s.value ?? "").trim();
    }
    return draft !== s.value;
  }

  async function save(s: SettingValue) {
    if (!hasChange(s)) return;
    setSavingKey(s.key);
    try {
      const value = coerceSettingValue(drafts[s.key], s.value_type);
      await api.updateSetting("general", s.key, value);
      toast({ tone: "success", title: "Enregistré", message: `${s.label} mis à jour` });
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

  return (
    <div>
      <PageHeader
        eyebrow="Paramètres"
        title="Paramètres généraux"
        subtitle="Personnalisez les paramètres clés de la plateforme. Modifications versionnées et auditées."
      />
      {loading && (
        <Card><div className="py-8 flex justify-center"><Spinner /></div></Card>
      )}
      {!loading && settings.length === 0 && (
        <Card>
          <EmptyState title="Aucun paramètre" description="Aucun paramètre dans cette catégorie." />
        </Card>
      )}
      {!loading && Object.entries(byGroup).map(([groupName, items]) => (
        <SettingsGroup key={groupName} title={groupName}>
          {items.map((s) => (
            <SettingRow
              key={s.key}
              setting={s}
              draft={drafts[s.key]}
              onChange={(v) => setDrafts((prev) => ({ ...prev, [s.key]: v }))}
              onSave={() => save(s)}
              saving={savingKey === s.key}
              dirty={hasChange(s)}
            />
          ))}
        </SettingsGroup>
      ))}
    </div>
  );
}

