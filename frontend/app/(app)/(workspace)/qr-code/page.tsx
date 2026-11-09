"use client";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Icon } from "@/components/Icon";

const USAGES = [
  { icon: "building-03", title: "Agences MA2E", desc: "Affichez le QR à l'accueil pour les nouveaux sociétaires." },
  { icon: "invoice-01", title: "Factures mensuelles", desc: "Imprimez-le sur les factures CIE / SODECI / GS2E." },
  { icon: "mail-01", title: "E-mails et SMS", desc: "Intégrez-le dans vos campagnes de communication." },
  { icon: "user-group", title: "Délégués syndicaux", desc: "Partagez le QR aux représentants du groupe." },
];

export default function QrCodePage() {
  const [chatUrl, setChatUrl] = useState<string>("");
  const [copied, setCopied] = useState(false);
  const [avatarOk, setAvatarOk] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setChatUrl(`${window.location.origin}/acces`);
    }
    const img = new window.Image();
    img.src = "/assistant-avatar.png";
    img.onerror = () => setAvatarOk(false);
  }, []);

  async function copyLink() {
    if (!chatUrl) return;
    try {
      await navigator.clipboard.writeText(chatUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  function downloadQr() {
    const svg = document.getElementById("ma2e-qr-svg") as SVGElement | null;
    if (!svg) return;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svg);
    const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ma2e-chat-qr.svg";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <header className="sa-page-header">
        <div className="sa-page-header__text">
          <nav aria-label="Fil d'Ariane">
            <ol className="sa-breadcrumb">
              <li><span>Console MA2E</span></li>
              <li><Icon name="arrow-right-01" className="i" /></li>
              <li><span aria-current="page">Accès par QR code</span></li>
            </ol>
          </nav>
          <h1 className="sa-page-title">Accès par QR code</h1>
          <p className="sa-page-desc">
            Distribuez ce code aux sociétaires : un scan ouvre l&apos;assistant MA2E directement sur leur appareil.
          </p>
        </div>
      </header>

      {/* Carte centrale : QR, lien public et actions alignées */}
      <section
        className="sa-card"
        aria-labelledby="qr-titre"
        style={{ maxWidth: 560, marginInline: "auto", alignItems: "center", textAlign: "center", padding: "var(--spacing-8)", gap: "var(--spacing-5)" }}
      >
        <div
          style={{
            position: "relative", background: "#FFFFFF", padding: 20,
            border: "3px solid rgb(var(--color-action-primary))", borderRadius: "var(--radius-sm)",
            lineHeight: 0,
          }}
        >
          {chatUrl ? (
            <QRCodeSVG
              id="ma2e-qr-svg"
              value={chatUrl}
              size={280}
              bgColor="#FFFFFF"
              fgColor="#00913D"
              level="H"
              includeMargin={false}
              role="img"
              aria-label={`QR code vers ${chatUrl}`}
              imageSettings={
                avatarOk
                  ? { src: "/assistant-avatar.png", height: 56, width: 56, excavate: true }
                  : undefined
              }
            />
          ) : (
            <div className="sa-skeleton sa-skeleton--block" style={{ width: 280, height: 280 }} />
          )}
          {!avatarOk && chatUrl && (
            <div
              aria-hidden="true"
              style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}
            >
              <span
                className="sa-avatar sa-avatar--48"
                style={{ boxShadow: "0 0 0 4px #FFFFFF" }}
              >
                M
              </span>
            </div>
          )}
        </div>

        <div>
          <h2 className="sa-h4" id="qr-titre" style={{ margin: 0 }}>
            Scannez avec l&apos;appareil photo de votre téléphone
          </h2>
          <p className="sa-text-soft" style={{ margin: "var(--spacing-2) 0 0" }}>
            L&apos;assistant MA2E s&apos;ouvre dans le navigateur, sans téléchargement ni installation.
          </p>
        </div>

        <div className="sa-field" style={{ width: "100%", textAlign: "left" }}>
          <label className="sa-label" htmlFor="qr-lien">Lien public</label>
          <input id="qr-lien" className="sa-input sa-mono" readOnly value={chatUrl || "—"} onFocus={(e) => e.currentTarget.select()} />
        </div>

        <div className="sa-form-actions" style={{ width: "100%", justifyContent: "center" }}>
          <button type="button" className="sa-btn sa-btn--secondary" onClick={copyLink}>
            <Icon name={copied ? "tick-02" : "copy-01"} className="i" />
            {copied ? "Lien copié" : "Copier le lien"}
          </button>
          <button type="button" className="sa-btn sa-btn--primary" onClick={downloadQr} disabled={!chatUrl}>
            <Icon name="download-02" className="i" />
            Télécharger le QR
          </button>
          <span className="sa-sr-only" role="status">{copied ? "Lien copié dans le presse-papiers" : ""}</span>
        </div>
      </section>

      {/* Cas d'usage + sécurité : 2 cartes de même hauteur */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" style={{ marginTop: "var(--spacing-6)", gridAutoRows: "1fr" }}>
        <section className="sa-card" aria-labelledby="qr-usages">
          <h2 className="sa-card__title" id="qr-usages">Cas d&apos;usage recommandés</h2>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            {USAGES.map((u) => (
              <li key={u.title} className="flex items-start gap-3">
                <span className="sa-icon-tile" style={{ width: 36, height: 36 }}>
                  <Icon name={u.icon} className="i" />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div className="sa-strong">{u.title}</div>
                  <div className="sa-text-soft">{u.desc}</div>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="sa-card" aria-labelledby="qr-secu">
          <h2 className="sa-card__title" id="qr-secu">Sécurité &amp; conformité</h2>
          <div className="sa-alert sa-alert--brand" style={{ flex: 1 }}>
            <Icon name="shield-user" className="i" />
            <div className="sa-alert__body">
              <p className="sa-alert__text" style={{ margin: 0 }}>
                Chaque session démarrée via QR est isolée, chiffrée en <strong>TLS 1.3</strong> et tracée
                dans le journal d&apos;audit <strong>ARTCI</strong>.
              </p>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
