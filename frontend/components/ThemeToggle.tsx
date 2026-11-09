"use client";
import { Icon } from "@/components/Icon";
import { useThemePref } from "@/lib/theme";
import type { ThemePref } from "@/lib/theme";

const OPTIONS: Array<{ value: ThemePref; icon: string; label: string }> = [
  { value: "light", icon: "sun-03", label: "Clair" },
  { value: "dark", icon: "moon-02", label: "Sombre" },
  { value: "system", icon: "computer", label: "Système" },
];

/** Sélecteur de thème clair / sombre / système (à placer dans le menu utilisateur). */
export default function ThemeToggle() {
  const [pref, setPref] = useThemePref();
  return (
    <div className="sa-theme-toggle" role="group" aria-label="Thème d’affichage">
      {OPTIONS.map((o) => (
        <button key={o.value} type="button" aria-pressed={pref === o.value} aria-label={`Thème ${o.label.toLowerCase()}`} title={o.label} onClick={() => setPref(o.value)}>
          <Icon name={o.icon} />
        </button>
      ))}
    </div>
  );
}
