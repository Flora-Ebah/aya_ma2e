"use client";
import Image from "next/image";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import { IconBrandWhatsApp } from "@/components/icons";

const WHATSAPP_NUMBER =
  process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || "22587137512";
const WHATSAPP_PRESET = encodeURIComponent(
  "Bonjour AYA, je suis sociétaire MA2E."
);

export default function AccesPage() {
  const router = useRouter();
  const [chosen, setChosen] = useState<"whatsapp" | "web" | null>(null);

  function pickWhatsApp() {
    setChosen("whatsapp");
    window.location.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${WHATSAPP_PRESET}`;
  }

  function pickWeb() {
    setChosen("web");
    router.push("/chat");
  }

  return (
    <div className="relative min-h-screen bg-[#F6FAF7] flex flex-col">
      {/* Rails dotted gauche / droite (cadre éditorial) */}
      <div aria-hidden className="pointer-events-none absolute inset-y-0 left-0 right-0 z-0">
        <div className="max-w-5xl mx-auto h-full relative">
          <div className="absolute top-0 bottom-0 left-2 sm:left-0 border-l border-dotted border-ink-200" />
          <div className="absolute top-0 bottom-0 right-2 sm:right-0 border-r border-dotted border-ink-200" />
        </div>
      </div>

      {/* Header — ultra minimal */}
      <header className="relative z-10 border-b border-ink-100/50">
        <div className="max-w-5xl mx-auto px-6 h-7 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Logo size={14} />
            <div className="text-[10.5px] font-medium text-ink-700 tracking-tight">
              MA2E
              <span className="text-ink-300 font-light mx-1">·</span>
              <span className="text-ink-400 font-light">Espace sociétaire</span>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-[9.5px] text-ink-400 font-light">
            <span className="w-1 h-1 rounded-full bg-primary-500" />
            En ligne
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10 flex-1 flex items-center justify-center">
        <div className="max-w-2xl w-full px-6 py-12 sm:py-16 text-center">
          {/* Assistant grand */}
          <div className="relative w-36 h-36 sm:w-44 sm:h-44 mx-auto mb-7">
            <div className="absolute inset-0 rounded-full bg-primary-500/10 ring-1 ring-primary-500/15" />
            <Image
              src="/assistant.png"
              alt="MA2E Assistant"
              width={176}
              height={176}
              className="relative w-full h-full object-contain"
              priority
            />
            <span className="absolute bottom-3 right-3 w-4 h-4 bg-accent-500 rounded-full ring-2 ring-white animate-pulse" />
          </div>

          <h1 className="text-[22px] sm:text-[26px] font-semibold text-ink-900 tracking-tight leading-[1.2]">
            Bonjour, je suis votre assistant MA2E.
          </h1>
          <p className="text-ink-500 mt-2 text-[12.5px] sm:text-[13px] font-light leading-relaxed max-w-sm mx-auto">
            M'identifier · Mettre à jour mes informations · Suivre mon dossier.
            <br />
            <span className="text-ink-400">Choisissez votre canal pour commencer.</span>
          </p>

          {/* 2 pills centered */}
          <div className="mt-9 flex flex-col items-center gap-4">
            {/* WhatsApp pill */}
            <button
              type="button"
              onClick={pickWhatsApp}
              disabled={chosen !== null}
              className="inline-flex items-center group relative disabled:opacity-60"
              aria-label="Ouvrir WhatsApp"
            >
              <span className="bg-[#25D366] group-hover:bg-[#1ebe5b] text-white pl-16 pr-7 py-3.5 transition relative overflow-hidden rounded-full">
                <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/15 to-white/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                <span className="text-[13.5px] font-semibold tracking-wide whitespace-nowrap relative">
                  {chosen === "whatsapp" ? "Ouverture" : "Ouvrir WhatsApp"}
                  <span className="inline-flex items-center align-middle ml-1.5 gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" style={{ animationDelay: "200ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" style={{ animationDelay: "400ms" }} />
                  </span>
                </span>
              </span>
              <span className="absolute left-0 w-12 h-12 rounded-full bg-white overflow-hidden ring-2 ring-white flex items-center justify-center text-[#25D366]">
                <IconBrandWhatsApp size={26} />
              </span>
              <span className="absolute -top-0.5 left-9 w-3 h-3 bg-accent-500 rounded-full ring-2 ring-white animate-pulse" />
            </button>

            {/* Web pill */}
            <button
              type="button"
              onClick={pickWeb}
              disabled={chosen !== null}
              className="inline-flex items-center group relative disabled:opacity-60"
              aria-label="Ouvrir le chat web"
            >
              <span className="bg-primary-600 group-hover:bg-primary-700 text-white pl-16 pr-7 py-3.5 transition relative overflow-hidden rounded-full">
                <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/15 to-white/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                <span className="text-[13.5px] font-semibold tracking-wide whitespace-nowrap relative">
                  {chosen === "web" ? "Ouverture" : "Ouvrir le Chat Web"}
                  <span className="inline-flex items-center align-middle ml-1.5 gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" style={{ animationDelay: "200ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" style={{ animationDelay: "400ms" }} />
                  </span>
                </span>
              </span>
              <span className="absolute left-0 w-12 h-12 rounded-full bg-white overflow-hidden ring-2 ring-white">
                <Image
                  src="/assistant-avatar.png"
                  alt="MA2E Assistant"
                  width={48}
                  height={48}
                  className="w-full h-full object-cover"
                />
              </span>
              <span className="absolute -top-0.5 left-9 w-3 h-3 bg-accent-500 rounded-full ring-2 ring-white animate-pulse" />
            </button>
          </div>

          <div className="mt-10 text-[10.5px] text-ink-400 font-light tracking-wide">
            <span className="text-ink-500 font-medium">Loi 2013-450</span> · TLS 1.3 · Audit HMAC-SHA256
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-ink-100/50">
        <div className="max-w-5xl mx-auto px-6 h-7 flex items-center justify-between text-[9.5px] text-ink-400 font-light">
          <div>© MA2E · Mutuelle des Agents de l'Eau et de l'Électricité</div>
          <div className="hidden sm:flex items-center gap-3">
            <a href="#" className="hover:text-ink-700 transition">Mentions légales</a>
            <a href="#" className="hover:text-ink-700 transition">Confidentialité</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
