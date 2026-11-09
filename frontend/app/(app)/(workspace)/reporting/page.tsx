"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";
import KpiSection from "./_KpiSection";
import TimelineChart, { Legend } from "./_TimelineChart";
import {
  AgentsCard, CardShell, ChannelsCard, FunnelCard, OcrCard, ReasonsCard,
} from "./_ReportingCards";
import { useReporting } from "./_useReporting";

const PERIODS = [
  { days: 7, label: "7 jours" },
  { days: 30, label: "30 jours" },
  { days: 90, label: "90 jours" },
];

export default function ReportingPage() {
  const [period, setPeriod] = useState(30);
  const { loading, overview, timeline, channels, reasons, agents, ocr, funnel } = useReporting(period);

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <nav aria-label="Fil d'Ariane">
            <ol className="sa-breadcrumb">
              <li><span>Pilotage</span></li>
              <li><Icon name="arrow-right-01" className="i" /></li>
              <li><span aria-current="page">Reporting</span></li>
            </ol>
          </nav>
          <h1 className="sa-page-title">Reporting &amp; statistiques</h1>
          <p className="sa-page-desc">
            Vue d&apos;ensemble de l&apos;activité d&apos;identification, performance opérationnelle et qualité.
          </p>
        </div>
        <div className="sa-page-actions">
          <div className="sa-segmented" role="group" aria-label="Période d'analyse">
            {PERIODS.map((p) => (
              <button
                key={p.days} type="button"
                aria-pressed={period === p.days}
                onClick={() => setPeriod(p.days)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <a
            href={api.exportStatsPdfUrl(period)}
            className="sa-btn sa-btn--primary"
            title="Export PDF du tableau de bord (US-26 AC4)"
          >
            <Icon name="pdf-01" className="i" />
            Export PDF
          </a>
        </div>
      </header>

      {loading && (
        <div aria-busy="true" aria-label="Chargement des statistiques" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="sa-skeleton sa-skeleton--kpi" />)}
        </div>
      )}

      {!loading && !overview && (
        <div className="sa-card">
          <div className="sa-empty">
            <Icon name="analytics-01" className="i" />
            <div className="sa-empty__title">Aucune donnée disponible</div>
            <p className="sa-empty__text">Les statistiques apparaîtront dès les premiers dossiers.</p>
          </div>
        </div>
      )}

      {!loading && overview && (
        <div className="flex flex-col gap-4">
          <KpiSection overview={overview} />

          <CardShell title="Évolution journalière" subtitle={`Dossiers créés, validés et refusés — ${period} derniers jours`} action={<Legend />}>
            <TimelineChart data={timeline} />
          </CardShell>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ gridAutoRows: "1fr" }}>
            {funnel && <FunnelCard funnel={funnel} />}
            <ChannelsCard channels={channels} />
            <ReasonsCard reasons={reasons} />
            <AgentsCard agents={agents} />
          </div>

          {ocr && <OcrCard ocr={ocr} />}
        </div>
      )}
    </>
  );
}
