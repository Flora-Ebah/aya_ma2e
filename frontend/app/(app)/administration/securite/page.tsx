"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";
import { Card, KpiCard, PageHeader, Spinner } from "@/components/ui";
import { SettingRow, SettingsGroup, coerceSettingValue } from "@/components/settings/SettingRow";
import type { SettingValue } from "@/components/settings/SettingRow";

type RetentionPreview = {
  policy: { retention_years: number; grace_days: number };
  summary: { total_dossiers: number; eligible_count: number; upcoming_count: number };
  eligible_for_purge: any[];
  upcoming_purges: any[];
};

export default function SecuritePage() {
  const toast = useToast();
  const [settings, setSettings] = useState<SettingValue[]>([]);
  const [drafts, setDrafts] = useState<Record<string, any>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retention, setRetention] = useState<RetentionPreview | null>(null);

  useEffect(() => { void boot(); }, []);

  async function boot() {
    try { await Promise.all([load(), loadRetention()]); }
    catch (e: any) { toast({ tone: "error", title: "Erreur", message: e.message }); }
    finally { setLoading(false); }
  }

  async function load() {
    const data = await api.getSettingsCategory("security");
    setSettings(data.settings);
    const d: Record<string, any> = {};
    data.settings.forEach((s: SettingValue) => (d[s.key] = s.value));
    setDrafts(d);
  }

  async function loadRetention() {
    try { setRetention(await api.retentionPreview()); }
    catch (e: any) { console.warn("retention preview indispo", e.message); }
  }

  const hasChange = (s: SettingValue) => {
    const draft = drafts[s.key];
    if (draft === undefined || draft === null) return false;
    return draft !== s.value;
  };

  async function save(s: SettingValue) {
    if (!hasChange(s)) return;
    setSavingKey(s.key);
    try {
      const value = coerceSettingValue(drafts[s.key], s.value_type);
      await api.updateSetting("security", s.key, value);
      toast({ tone: "success", title: "Enregistré", message: s.label });
      await Promise.all([load(), loadRetention()]);
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
        eyebrow="Administration"
        title="Sécurité & ARTCI"
        subtitle="Politique de mots de passe, gestion des sessions et durée de conservation des données à caractère personnel (ARTCI art. 36)."
      />
      {retention && <RetentionDashboard retention={retention} />}
      {loading && <Card><div className="py-8 flex justify-center"><Spinner /></div></Card>}
      {!loading && Object.entries(byGroup).map(([groupName, items]) => (
        <SettingsGroup
          key={groupName}
          title={groupName}
          icon={<Icon name="lock-key" className="i" />}
        >
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

function RetentionDashboard({ retention }: { retention: RetentionPreview }) {
  const { summary, policy } = retention;
  return (
    <section style={{ marginBottom: 24 }} aria-label="Tableau de bord rétention">
      <div className="sa-page-header" style={{ marginBottom: 12 }}>
        <h2 className="sa-h4" style={{ margin: 0 }}>Tableau de bord rétention</h2>
        <span className="sa-badge sa-badge--neutral">
          Politique : {policy.retention_years} ans + {policy.grace_days} j de grâce
        </span>
      </div>
      <div className="sa-grid sa-grid--stats-3">
        <Metric label="Total dossiers" value={summary.total_dossiers} hint="Sur la plateforme MA2E" />
        <Metric
          label="Éligibles à la purge"
          value={summary.eligible_count}
          hint="Au-delà du délai légal"
          tone={summary.eligible_count > 0 ? "warn" : "ok"}
        />
        <Metric label="Échéance < 90 j" value={summary.upcoming_count} hint="Action conseillée bientôt" tone="info" />
      </div>
      {retention.eligible_for_purge.length > 0 && (
        <div className="sa-alert sa-alert--warning" role="status" style={{ marginTop: 12 }}>
          <Icon name="alert-02" className="i" />
          <div className="sa-alert__body">
            <div className="sa-alert__text">
              <strong>{retention.eligible_for_purge.length}</strong> dossier(s) ont dépassé la durée
              légale. La purge automatique sera implémentée en Phase B (tâche planifiée). Pour
              l&apos;instant, exportez les dossiers visés via la page Dossiers puis archivez-les manuellement.
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value, hint, tone = "ok" }: {
  label: string; value: number; hint: string; tone?: "ok" | "warn" | "info";
}) {
  const icon = tone === "warn" ? "alert-02" : tone === "info" ? "clock-01" : "checkmark-circle-02";
  return <KpiCard label={label} value={value} meta={hint} icon={icon} iconTone={tone} valueTone={tone === "warn" ? "danger" : "default"} />;
}
