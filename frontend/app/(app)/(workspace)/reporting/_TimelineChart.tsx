import type { TimelinePoint } from "./_types";

const W = 720;
const H = 220;
const PAD_L = 34, PAD_R = 14, PAD_T = 14, PAD_B = 30;
const INNER_W = W - PAD_L - PAD_R;
const INNER_H = H - PAD_T - PAD_B;

/** Séries : couleur du jeton `chart-N` + motif de trait (la couleur n'est jamais seule). */
export const SERIES = [
  { key: "created", label: "Créés", color: "rgb(var(--color-chart-1))", dash: undefined as string | undefined },
  { key: "validated", label: "Validés", color: "rgb(var(--color-chart-2))", dash: "6 3" },
  { key: "rejected", label: "Refusés", color: "rgb(var(--color-chart-5))", dash: "2 3" },
] as const;

export default function TimelineChart({ data }: { data: TimelinePoint[] }) {
  if (data.length === 0) {
    return (
      <div className="sa-empty sa-empty--compact">
        <div className="sa-empty__title">Aucune activité dans la période</div>
      </div>
    );
  }

  const maxVal = Math.max(1, ...data.flatMap((d) => [d.created, d.validated, d.rejected]));
  const stepX = data.length > 1 ? INNER_W / (data.length - 1) : INNER_W;

  const pathFor = (vals: number[]) =>
    vals.map((v, i) => {
      const x = PAD_L + i * stepX;
      const y = PAD_T + INNER_H - (v / maxVal) * INNER_H;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((r) => ({
    y: PAD_T + INNER_H * (1 - r),
    label: Math.round(maxVal * r),
  }));

  const xLabels = [0, Math.floor(data.length / 2), data.length - 1].map((i) => {
    const dt = new Date(data[i].date);
    return {
      x: PAD_L + i * stepX,
      label: dt.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }),
    };
  });

  const total = (k: "created" | "validated" | "rejected") => data.reduce((n, d) => n + d[k], 0);
  const summary = `Évolution journalière sur ${data.length} jours : ${total("created")} dossiers créés, `
    + `${total("validated")} validés, ${total("rejected")} refusés.`;

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: "auto", maxHeight: 260 }} role="img" aria-label={summary}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD_L} x2={W - PAD_R} y1={t.y} y2={t.y}
              stroke="rgb(var(--color-border-default))" strokeDasharray="2 3"
            />
            <text x={PAD_L - 6} y={t.y + 3} textAnchor="end" fontSize="10" fill="rgb(var(--color-text-secondary))">
              {t.label}
            </text>
          </g>
        ))}
        {SERIES.map((s) => (
          <path
            key={s.key}
            d={pathFor(data.map((d) => d[s.key]))}
            fill="none" stroke={s.color} strokeWidth="2.25" strokeDasharray={s.dash}
            strokeLinecap="round" strokeLinejoin="round"
          />
        ))}
        {xLabels.map((l, i) => (
          <text key={i} x={l.x} y={H - 8} textAnchor="middle" fontSize="10" fill="rgb(var(--color-text-secondary))">
            {l.label}
          </text>
        ))}
      </svg>

      <details style={{ marginTop: "var(--spacing-3)" }}>
        <summary className="sa-link" style={{ cursor: "pointer", width: "fit-content" }}>
          Afficher les données sous forme de tableau
        </summary>
        <div className="sa-table-wrap" style={{ marginTop: "var(--spacing-3)", maxHeight: 280, overflowY: "auto" }}>
          <table className="sa-table sa-table--compact">
            <caption className="sa-sr-only">Dossiers créés, validés et refusés par jour</caption>
            <thead>
              <tr>
                <th scope="col">Jour</th>
                <th scope="col" className="is-num">Créés</th>
                <th scope="col" className="is-num">Validés</th>
                <th scope="col" className="is-num">Refusés</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.date}>
                  <th scope="row" style={{ position: "static", textTransform: "none", letterSpacing: 0, background: "transparent", fontWeight: 500 }}>
                    {new Date(d.date).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}
                  </th>
                  <td className="is-num">{d.created}</td>
                  <td className="is-num">{d.validated}</td>
                  <td className="is-num">{d.rejected}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

/** Légende : pastille colorée + motif de trait + libellé. */
export function Legend() {
  return (
    <ul className="sa-legend" style={{ display: "flex", gap: "var(--spacing-4)", listStyle: "none", margin: 0, padding: 0, flexWrap: "wrap" }}>
      {SERIES.map((s) => (
        <li key={s.key} className="inline-flex items-center gap-2 sa-text-soft">
          <svg width="22" height="8" aria-hidden="true">
            <line x1="1" x2="21" y1="4" y2="4" stroke={s.color} strokeWidth="2.5" strokeDasharray={s.dash} strokeLinecap="round" />
          </svg>
          {s.label}
        </li>
      ))}
    </ul>
  );
}
