"use client";
import { Card, PageHeader, Spinner } from "@/components/ui";
import { SettingRow, SettingsGroup } from "@/components/settings/SettingRow";
import { useIntegrationsSettings } from "./_useIntegrationsSettings";
import VerifyReferentialCard from "./_VerifyReferentialCard";
import WebhookDeliveriesCard from "./_WebhookDeliveriesCard";

export default function IntegrationsPage() {
  const { loading, byGroup, drafts, savingKey, setDraft, hasChange, save } = useIntegrationsSettings();

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Intégrations externes"
        subtitle="Référentiel des agents employeurs et notifications vers le système comptable MA2E."
      />

      {loading && <Card><div className="py-8 flex justify-center"><Spinner /></div></Card>}

      {!loading && Object.entries(byGroup).map(([groupName, items]) => (
        <SettingsGroup key={groupName} title={groupName}>
          {items.map((s) => (
            <SettingRow
              key={s.key}
              setting={s}
              draft={drafts[s.key]}
              onChange={(v) => setDraft(s.key, v)}
              onSave={() => save(s)}
              saving={savingKey === s.key}
              dirty={hasChange(s)}
            />
          ))}
        </SettingsGroup>
      ))}

      {!loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <VerifyReferentialCard />
          <WebhookDeliveriesCard />
        </div>
      )}
    </div>
  );
}
