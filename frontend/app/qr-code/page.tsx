"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { getToken } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FloatingChatButton from "@/components/FloatingChatButton";
import { IconCheck, IconCopy, IconDownload, IconQrCode } from "@/components/icons";

export default function QrCodePage() {
  const router = useRouter();
  const [chatUrl, setChatUrl] = useState<string>("");
  const [copied, setCopied] = useState(false);
  const [avatarOk, setAvatarOk] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    if (typeof window !== "undefined") {
      setChatUrl(`${window.location.origin}/acces`);
    }
    const img = new window.Image();
    img.src = "/assistant-avatar.png";
    img.onerror = () => setAvatarOk(false);
  }, [router]);

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
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar />
      <FloatingChatButton />
      <main className="lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 py-10">
          <div className="flex items-end justify-between mb-8 flex-wrap gap-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.12em] text-primary-600 font-semibold mb-1.5">
                Console MA2E
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
                Accès par QR Code
              </h1>
              <p className="text-ink-500 mt-1 text-[15px] font-light">
                Distribuez ce code aux sociétaires — un scan ouvre l'assistant MA2E directement sur leur appareil.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={copyLink}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-ink-50 text-ink-700 text-[13px] font-normal rounded-sm px-3 py-2 border border-ink-200 transition"
              >
                {copied ? (
                  <>
                    <IconCheck size={14} />
                    Lien copié
                  </>
                ) : (
                  <>
                    <IconCopy size={14} />
                    Copier le lien
                  </>
                )}
              </button>
              <button
                onClick={downloadQr}
                className="inline-flex items-center gap-1.5 bg-primary-600 hover:bg-primary-700 text-white text-[13px] font-normal rounded-sm px-3 py-2 transition shadow-sm"
              >
                <IconDownload size={14} />
                Télécharger le QR
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3">
              <div className="bg-white border border-ink-200 rounded-sm shadow-soft p-10 flex flex-col items-center justify-center min-h-[600px]">
                <div className="bg-white p-8 border-4 border-primary-600 rounded-sm relative">
                  {chatUrl ? (
                    <QRCodeSVG
                      id="ma2e-qr-svg"
                      value={chatUrl}
                      size={360}
                      bgColor="#FFFFFF"
                      fgColor="#00913D"
                      level="H"
                      includeMargin={false}
                      imageSettings={
                        avatarOk
                          ? {
                              src: "/assistant-avatar.png",
                              height: 70,
                              width: 70,
                              excavate: true,
                            }
                          : undefined
                      }
                    />
                  ) : (
                    <div className="w-[360px] h-[360px] bg-ink-100 animate-pulse rounded-sm" />
                  )}
                  {!avatarOk && chatUrl && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 text-white flex items-center justify-center text-2xl font-bold ring-4 ring-white shadow-md">
                        M
                      </div>
                    </div>
                  )}
                </div>
                <div className="mt-8 text-center max-w-md">
                  <div className="text-base font-semibold text-ink-900">
                    Scannez avec l'appareil photo de votre téléphone
                  </div>
                  <div className="text-sm text-ink-500 mt-1.5 font-light">
                    L'assistant MA2E s'ouvre automatiquement dans le navigateur, sans
                    téléchargement ni installation.
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              <div className="bg-white border border-ink-200 rounded-sm shadow-soft p-6">
                <div className="text-[10px] uppercase tracking-[0.12em] text-primary-600 font-semibold mb-3">
                  Lien public
                </div>
                <div className="bg-ink-50 rounded-sm p-4 text-[13px] font-mono text-ink-700 break-all border border-ink-100">
                  {chatUrl || "—"}
                </div>
              </div>

              <div className="bg-white border border-ink-200 rounded-sm shadow-soft p-6">
                <div className="text-[10px] uppercase tracking-[0.12em] text-primary-600 font-semibold mb-3">
                  Cas d'usage recommandés
                </div>
                <ul className="space-y-3 text-sm text-ink-700 font-light">
                  <li className="flex gap-3">
                    <span className="w-1 bg-primary-300 rounded-sm shrink-0" />
                    <div>
                      <strong className="font-semibold text-ink-900 block">
                        Agences MA2E
                      </strong>
                      <span className="text-ink-500">
                        Affichez le QR à l'accueil pour les nouveaux sociétaires.
                      </span>
                    </div>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-1 bg-primary-300 rounded-sm shrink-0" />
                    <div>
                      <strong className="font-semibold text-ink-900 block">
                        Factures mensuelles
                      </strong>
                      <span className="text-ink-500">
                        Imprimez-le sur les factures CIE / SODECI / GS2E.
                      </span>
                    </div>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-1 bg-primary-300 rounded-sm shrink-0" />
                    <div>
                      <strong className="font-semibold text-ink-900 block">
                        Communications email & SMS
                      </strong>
                      <span className="text-ink-500">
                        Intégrez-le dans vos campagnes de communication.
                      </span>
                    </div>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-1 bg-primary-300 rounded-sm shrink-0" />
                    <div>
                      <strong className="font-semibold text-ink-900 block">
                        Délégués syndicaux
                      </strong>
                      <span className="text-ink-500">
                        Partagez le QR aux représentants du groupe.
                      </span>
                    </div>
                  </li>
                </ul>
              </div>

              <div className="bg-gradient-to-br from-primary-600 to-primary-800 text-white rounded-sm p-6 shadow-card relative overflow-hidden">
                <div className="absolute -bottom-12 -right-12 w-32 h-32 bg-accent-400/15 rounded-full blur-2xl" />
                <div className="relative">
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.12em] font-semibold mb-2 text-white/90">
                    <IconQrCode size={14} />
                    Sécurité & conformité
                  </div>
                  <div className="text-sm leading-relaxed text-white/85 font-light">
                    Chaque session démarrée via QR est isolée, chiffrée{" "}
                    <strong className="text-accent-300 font-semibold">TLS 1.3</strong>,
                    et tracée dans le journal d'audit{" "}
                    <strong className="text-accent-300 font-semibold">ARTCI</strong>.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
