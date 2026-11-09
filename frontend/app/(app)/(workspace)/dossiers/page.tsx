"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";
import AdvancedFiltersPanel from "./_AdvancedFiltersPanel";
import DossiersTable from "./_DossiersTable";
import DossiersToolbar from "./_DossiersToolbar";
import ListPagination from "./_ListPagination";
import StatsHeader from "./_StatsHeader";
import { countActiveAdvanced, DEFAULT_ADVANCED, type AdvancedFilters } from "./_types";
import { useDossiersList } from "./_useDossiersList";

const PAGE_SIZE = 15;

/** La recherche du header envoie vers `/dossiers?q=…` : la page enveloppe son contenu dans Suspense (useSearchParams). */
export default function DossiersPage() {
  return (
    <Suspense fallback={null}>
      <DossiersPageContent />
    </Suspense>
  );
}

function DossiersPageContent() {
  const searchParams = useSearchParams();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [advanced, setAdvanced] = useState<AdvancedFilters>(DEFAULT_ADVANCED);
  const [pendingAdvanced, setPendingAdvanced] = useState<AdvancedFilters>(DEFAULT_ADVANCED);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const { dossiers, stats, loading, error, reload } = useDossiersList(statusFilter, advanced);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelectAll(ids: string[]) {
    setSelected((prev) => {
      const allOn = ids.every((id) => prev.has(id));
      const next = new Set(prev);
      if (allOn) ids.forEach((id) => next.delete(id));
      else ids.forEach((id) => next.add(id));
      return next;
    });
  }

  function printSelection() {
    const ids = Array.from(selected);
    if (!ids.length) return;
    window.open(api.bulkFichesPdfUrl(ids), "_blank", "noopener");
  }

  const filtered = useMemo(() => {
    if (!search.trim()) return dossiers;
    const q = search.toLowerCase();
    return dossiers.filter((d) =>
      d.dossier_number.toLowerCase().includes(q) ||
      (d.end_user_name || "").toLowerCase().includes(q) ||
      (d.matricule || "").toLowerCase().includes(q) ||
      (d.end_user_contact || "").toLowerCase().includes(q)
    );
  }, [dossiers, search]);

  // Pré-remplit / met à jour la recherche depuis `?q=` (recherche du header).
  const qParam = searchParams.get("q");
  useEffect(() => {
    if (qParam !== null) setSearch(qParam);
  }, [qParam]);

  // Retour en page 1 dès que le jeu de résultats change.
  useEffect(() => { setPage(1); }, [search, statusFilter, advanced]);

  const pageItems = useMemo(
    () => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [filtered, page],
  );

  const activeCount = countActiveAdvanced(advanced);
  const exportUrl = api.exportDossiersUrl({
    status: statusFilter || undefined,
    employeur_code: advanced.employeur_code || undefined,
    since: advanced.since || undefined,
    until: advanced.until || undefined,
  });

  function toggleAdvanced() {
    setPendingAdvanced(advanced);
    setAdvancedOpen((v) => !v);
  }

  function onAdvancedApply() {
    setAdvanced(pendingAdvanced);
  }

  function onAdvancedReset() {
    setPendingAdvanced(DEFAULT_ADVANCED);
    setAdvanced(DEFAULT_ADVANCED);
  }

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <nav aria-label="Fil d'Ariane">
            <ol className="sa-breadcrumb">
              <li><span>Console MA2E</span></li>
              <li><Icon name="arrow-right-01" className="i" /></li>
              <li><span aria-current="page">Dossiers</span></li>
            </ol>
          </nav>
          <h1 className="sa-page-title">Dossiers d&apos;identification</h1>
          <p className="sa-page-desc">Validation et suivi des enrôlements sociétaires.</p>
        </div>
        <div className="sa-page-actions">
          <button type="button" className="sa-btn sa-btn--ghost" onClick={reload}>
            <Icon name="refresh" className="i" />
            Actualiser
          </button>
          <a
            href={exportUrl}
            className="sa-btn sa-btn--primary"
            download
            title="Export Excel des dossiers filtrés (US-25)"
          >
            <Icon name="download-02" className="i" />
            Exporter Excel
          </a>
        </div>
      </header>

      {stats && (
        <StatsHeader stats={stats} activeStatus={statusFilter} onSelect={setStatusFilter} />
      )}

      <section className="sa-card" style={{ padding: 0, gap: 0 }} aria-label="Liste des dossiers">
        <DossiersToolbar
          search={search}
          onSearchChange={setSearch}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          advancedOpen={advancedOpen}
          onToggleAdvanced={toggleAdvanced}
          activeAdvancedCount={activeCount}
        />

        {advancedOpen && (
          <AdvancedFiltersPanel
            value={pendingAdvanced}
            onChange={setPendingAdvanced}
            onApply={onAdvancedApply}
            onReset={onAdvancedReset}
          />
        )}

        {error && (
          <div className="sa-alert sa-alert--error" role="alert" style={{ margin: "var(--spacing-3) var(--spacing-5)" }}>
            <Icon name="alert-circle" className="i" />
            <div className="sa-alert__body"><p className="sa-alert__text">{error}</p></div>
          </div>
        )}

        <div
          className="sa-pagination__info"
          style={{ padding: "0 var(--spacing-5) var(--spacing-3)" }}
          aria-live="polite"
        >
          {filtered.length} dossier{filtered.length > 1 ? "s" : ""}
        </div>

        {selected.size > 0 && (
          <div
            className="sa-row"
            style={{
              gap: 8,
              justifyContent: "space-between",
              padding: "8px 12px",
              marginBottom: 8,
              background: "rgb(var(--color-brand-primary-subtle))",
              borderRadius: 8,
              alignItems: "center",
            }}
          >
            <span className="sa-strong">
              {selected.size} dossier{selected.size > 1 ? "s" : ""} sélectionné{selected.size > 1 ? "s" : ""}
            </span>
            <div className="sa-row" style={{ gap: 6 }}>
              <button
                type="button"
                className="sa-btn sa-btn--primary sa-btn--sm"
                onClick={printSelection}
              >
                <Icon name="printer" className="i" />
                Imprimer les fiches sélectionnées
              </button>
              <button
                type="button"
                className="sa-btn sa-btn--ghost sa-btn--sm"
                onClick={() => setSelected(new Set())}
              >
                Tout désélectionner
              </button>
            </div>
          </div>
        )}
        <DossiersTable
          loading={loading}
          items={pageItems}
          search={search}
          hasFilter={!!statusFilter}
          onDeleted={reload}
          selected={selected}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
        />

        <ListPagination page={page} pageSize={PAGE_SIZE} total={filtered.length} onPageChange={setPage} />
      </section>
    </>
  );
}
