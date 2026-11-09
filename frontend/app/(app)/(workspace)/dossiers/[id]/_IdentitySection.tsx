"use client";
import { Icon } from "@/components/Icon";
import { FIELD_LABELS } from "./_constants";
import { SectionBlock } from "./_SectionBlock";

type Props = {
  recto: any;
  verso: any;
  signatureUrl?: string | null;
  onZoom: (url: string) => void;
};

export default function IdentitySection({ recto, verso, signatureUrl, onZoom }: Props) {
  const versoParsed = verso?.mrz_data?.parsed;
  const hasVersoMrz = versoParsed && Object.keys(versoParsed).length > 0;
  const hasSignature = typeof signatureUrl === "string" && signatureUrl.length > 0;
  const cols = hasSignature ? "md:grid-cols-3" : "md:grid-cols-2";

  return (
    <SectionBlock
      id="identite"
      title="Identité officielle"
      subtitle="Pièces d'identité · OCR Mindee · Signature manuscrite"
    >
      <div className={`grid grid-cols-1 ${cols} gap-4`} style={{ gridAutoRows: "1fr" }}>
        <PhotoCard piece={recto} face="recto" onZoom={onZoom} />
        <PhotoCard piece={verso} face="verso" onZoom={onZoom} />
        {hasSignature && (
          <SignatureCard url={signatureUrl!} onZoom={onZoom} />
        )}
      </div>

      <DataList
        title="Identité (recto)"
        data={recto?.ocr_data || {}}
        total={recto?.ocr_confidence != null ? `Confiance OCR ${Math.round(recto.ocr_confidence * 100)} %` : null}
      />

      {hasVersoMrz && (
        <DataList
          title="Zone MRZ (verso · ICAO 9303)"
          data={versoParsed}
          mrzLines={[verso.mrz_data.line1, verso.mrz_data.line2].filter(Boolean) as string[]}
          total={verso?.ocr_confidence != null ? `Confiance OCR ${Math.round(verso.ocr_confidence * 100)} %` : null}
        />
      )}
    </SectionBlock>
  );
}

function PhotoCard({ piece, face, onZoom }: {
  piece: any; face: "recto" | "verso"; onZoom: (url: string) => void;
}) {
  if (!piece) {
    return (
      <div className="sa-empty sa-empty--compact" style={{ border: "1px dashed rgb(var(--color-border-strong))", borderRadius: "var(--radius-sm)" }}>
        <Icon name="image-01" className="i" />
        <div className="sa-empty__title">Pièce {face} absente</div>
      </div>
    );
  }
  const imageUrl = piece.storage_key?.startsWith("http") ? piece.storage_key : null;
  const conf = piece.ocr_confidence != null ? Math.round(piece.ocr_confidence * 100) : null;

  return (
    <figure
      style={{
        margin: 0, border: "1px solid rgb(var(--color-border-default))", borderRadius: "var(--radius-sm)",
        overflow: "hidden", display: "flex", flexDirection: "column",
      }}
    >
      {imageUrl ? (
        <button
          type="button" onClick={() => onZoom(imageUrl)}
          aria-label={`Agrandir la pièce ${face}`}
          style={{ display: "block", width: "100%", padding: 0, border: 0, cursor: "zoom-in", background: "rgb(var(--color-bg-surface-subtle))" }}
        >
          <img src={imageUrl} alt={`Pièce ${face}`} style={{ width: "100%", height: 176, objectFit: "cover", display: "block" }} />
        </button>
      ) : (
        <div className="sa-thumb" style={{ width: "100%", height: 176, aspectRatio: "auto", border: 0, borderRadius: 0 }}>
          <Icon name="image-01" className="i" />
        </div>
      )}
      <figcaption
        className="sa-row"
        style={{
          justifyContent: "space-between", padding: "var(--spacing-2) var(--spacing-3)",
          borderTop: "1px solid rgb(var(--color-border-subtle))", background: "rgb(var(--color-bg-surface-subtle))",
        }}
      >
        <span className="sa-section-title__label">{face}</span>
        {conf != null && (
          <span className={`sa-badge ${conf >= 80 ? "sa-badge--ok" : conf >= 50 ? "sa-badge--warn" : "sa-badge--error"}`}>
            <Icon name={conf >= 80 ? "checkmark-circle-02" : "alert-circle"} className="i" />
            {conf} % OCR
          </span>
        )}
      </figcaption>
    </figure>
  );
}

function SignatureCard({ url, onZoom }: { url: string; onZoom: (u: string) => void }) {
  return (
    <figure
      style={{
        margin: 0,
        border: "1px solid rgb(var(--color-border-default))",
        borderRadius: "var(--radius-sm)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <button
        type="button"
        onClick={() => onZoom(url)}
        aria-label="Agrandir la signature"
        style={{
          display: "block",
          width: "100%",
          padding: 0,
          border: 0,
          cursor: "zoom-in",
          background: "#fff",
        }}
      >
        <img
          src={url}
          alt="Signature manuscrite"
          style={{ width: "100%", height: 176, objectFit: "contain", display: "block", padding: 8 }}
        />
      </button>
      <figcaption
        className="sa-row"
        style={{
          justifyContent: "space-between",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderTop: "1px solid rgb(var(--color-border-subtle))",
          background: "rgb(var(--color-bg-surface-subtle))",
        }}
      >
        <span className="sa-section-title__label">signature</span>
        <span className="sa-badge sa-badge--neutral">
          <Icon name="edit-02" className="i" />
          manuscrite
        </span>
      </figcaption>
    </figure>
  );
}

function DataList({ title, data, total, mrzLines }: {
  title: string;
  data: Record<string, any>;
  total?: string | null;
  mrzLines?: string[];
}) {
  const entries = Object.entries(data || {}).filter(([, v]) => v != null && v !== "");
  return (
    <div>
      <h3 className="sa-h5" style={{ margin: "0 0 var(--spacing-3)" }}>{title}</h3>
      {mrzLines && mrzLines.length > 0 && (
        <pre
          className="sa-mono"
          style={{
            margin: "0 0 var(--spacing-3)", padding: "var(--spacing-3)", overflowX: "auto", fontSize: 12,
            background: "rgb(var(--color-bg-surface-subtle))", border: "1px dashed rgb(var(--color-border-strong))",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {mrzLines.join("\n")}
        </pre>
      )}
      {entries.length === 0 ? (
        <p className="sa-help" style={{ margin: 0 }}>Aucune donnée extraite.</p>
      ) : (
        <dl className="sa-kv">
          {entries.map(([k, v]) => (
            <div key={k} style={{ display: "contents" }}>
              <dt>{FIELD_LABELS[k] || k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
          {total && (
            <>
              <dt>Confiance</dt>
              <dd className="sa-strong">{total}</dd>
            </>
          )}
        </dl>
      )}
    </div>
  );
}
