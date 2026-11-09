"use client";
import { Icon } from "@/components/Icon";
import { scrollToSection, TOC } from "./_constants";

type Props = {
  activeSection: string;
  signedConsentsCount: number;
};

/** Sommaire collant du dossier (sous-navigation par ancres) + rappel de conformité ARTCI. */
export default function TocSidebar({ activeSection, signedConsentsCount }: Props) {
  return (
    <>
    {/* < 1024 px : sommaire compact au-dessus du contenu (défilement horizontal des puces, pas de scroll vertical) */}
    <nav className="lg:hidden w-full" aria-label="Sections du dossier (compact)">
      <ul className="flex flex-wrap gap-2" style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {TOC.map((item, idx) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className="sa-chip"
              aria-current={activeSection === item.id ? "true" : undefined}
              onClick={(e) => {
                e.preventDefault();
                scrollToSection(item.id);
              }}
            >
              <span className="sa-mono">{String(idx + 1).padStart(2, "0")}</span> {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
    <aside className="hidden lg:block w-60 shrink-0 self-stretch" aria-label="Sommaire du dossier">
      <div className="sticky flex flex-col gap-4" style={{ top: "calc(var(--size-header) + 16px)" }}>
        <div className="sa-card" style={{ padding: "var(--spacing-3)" }}>
          <div className="sa-section-title__label" style={{ padding: "var(--spacing-2) var(--spacing-3)" }}>
            Sommaire
          </div>
          <nav aria-label="Sections du dossier">
            <ul className="sa-nav sa-nav--sub" style={{ padding: 0 }}>
              {TOC.map((item, idx) => {
                const active = activeSection === item.id;
                return (
                  <li key={item.id}>
                    <a
                      href={`#${item.id}`}
                      className="sa-nav-item"
                      style={{ paddingLeft: "var(--spacing-3)", minHeight: 32, fontSize: "var(--font-size-body-sm)" }}
                      aria-current={active ? "true" : undefined}
                      onClick={(e) => {
                        e.preventDefault();
                        scrollToSection(item.id);
                      }}
                    >
                      <span
                        className="sa-mono"
                        style={{ fontSize: 11, color: "rgb(var(--color-text-secondary))", minWidth: 18 }}
                      >
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <span className="sa-nav-item__label">{item.label}</span>
                    </a>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>

        <div className="sa-card" style={{ padding: "var(--spacing-4)", gap: "var(--spacing-2)" }}>
          <div className="sa-section-title__label">Conformité ARTCI</div>
          <div className="sa-row" style={{ gap: 8, flexWrap: "nowrap" }}>
            <Icon name="shield-user" className="i" />
            <span>
              <strong className="sa-strong">{signedConsentsCount} / 3</strong> consentements signés
            </span>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
}
