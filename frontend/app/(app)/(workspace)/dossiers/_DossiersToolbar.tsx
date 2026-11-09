"use client";
import { Icon } from "@/components/Icon";
import { STATUS_FILTERS } from "./_types";

type Props = {
  search: string;
  onSearchChange: (v: string) => void;
  statusFilter: string;
  onStatusFilterChange: (v: string) => void;
  advancedOpen: boolean;
  onToggleAdvanced: () => void;
  activeAdvancedCount: number;
};

/**
 * Barre de filtres sur UNE ligne alignée : recherche (extensible), statut,
 * « Plus de filtres » (avec compteur de filtres actifs).
 */
export default function DossiersToolbar({
  search, onSearchChange, statusFilter, onStatusFilterChange,
  advancedOpen, onToggleAdvanced, activeAdvancedCount,
}: Props) {
  return (
    <div className="sa-toolbar" style={{ flexWrap: "nowrap", alignItems: "center" }} role="search">
      <div className="sa-input-group" style={{ flex: "1 1 220px", minWidth: 0 }}>
        <Icon name="search-01" className="i" />
        <input
          type="search"
          className="sa-input"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Rechercher un dossier, un nom, un matricule…"
          aria-label="Rechercher un dossier"
        />
      </div>

      <select
        className="sa-select"
        style={{ flex: "0 1 200px", minWidth: 0 }}
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value)}
        aria-label="Filtrer par statut"
      >
        {STATUS_FILTERS.map((f) => (
          <option key={f.key} value={f.key}>
            {f.key === "" ? "Tous les statuts" : f.label}
          </option>
        ))}
      </select>

      <button
        type="button"
        className="sa-btn sa-btn--outline"
        style={{ flex: "none" }}
        onClick={onToggleAdvanced}
        aria-expanded={advancedOpen}
        aria-controls="dossiers-filtres-avances"
      >
        <Icon name="filter" className="i" />
        <span className="hidden sm:inline">Plus de filtres</span>
        {activeAdvancedCount > 0 && (
          <span className="sa-badge sa-badge--solid" aria-label={`${activeAdvancedCount} filtres actifs`}>
            {activeAdvancedCount}
          </span>
        )}
      </button>
    </div>
  );
}
