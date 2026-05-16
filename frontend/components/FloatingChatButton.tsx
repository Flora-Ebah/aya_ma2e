"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

export default function FloatingChatButton() {
  const [imgError, setImgError] = useState(false);

  return (
    <Link
      href="/chat"
      target="_blank"
      className="fixed bottom-6 right-6 z-30 inline-flex items-center group"
      title="Ouvrir le chat"
    >
      <div className="bg-primary-600 group-hover:bg-primary-700 text-white pl-14 pr-6 py-3 shadow-floating transition relative overflow-hidden rounded-full">
        <div className="absolute inset-0 bg-gradient-to-r from-primary-500/0 via-white/10 to-primary-500/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
        <span className="text-[13px] font-medium tracking-wide whitespace-nowrap relative">
          Ouvrir le chat
          <span className="inline-flex ml-1 gap-0.5">
            <span className="opacity-60 group-hover:animate-pulse">.</span>
            <span className="opacity-60 group-hover:animate-pulse" style={{ animationDelay: "150ms" }}>.</span>
            <span className="opacity-60 group-hover:animate-pulse" style={{ animationDelay: "300ms" }}>.</span>
          </span>
        </span>
      </div>
      <div className="absolute left-0 w-12 h-12 rounded-full bg-white shadow-md overflow-hidden ring-2 ring-white">
        {!imgError ? (
          <Image
            src="/assistant-avatar.png"
            alt="MA2E Assistant"
            width={48}
            height={48}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary-400 via-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-lg">
            M
          </div>
        )}
      </div>
      <span className="absolute -top-0.5 left-9 w-3 h-3 bg-accent-500 rounded-full ring-2 ring-white animate-pulse" />
    </Link>
  );
}
