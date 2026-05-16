"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import FloatingChatButton from "@/components/FloatingChatButton";
import { IconBuilding } from "@/components/icons";

export default function EmployeursPage() {
  const router = useRouter();
  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  return (
    <div className="min-h-screen bg-[#F6FAF7]">
      <Sidebar />
      <FloatingChatButton />
      <main className="lg:pl-64">
        <div className="max-w-4xl mx-auto px-6 py-12 text-center">
          <div className="inline-flex w-14 h-14 rounded-sm bg-primary-50 text-primary-500 items-center justify-center mb-4">
            <IconBuilding size={26} />
          </div>
          <h1 className="text-2xl font-semibold text-ink-900 mb-1">Référentiel employeurs</h1>
          <p className="text-ink-500 text-[14px] font-light max-w-md mx-auto">
            Liste fermée des sociétés du périmètre MA2E (SODECI, CIE, GS2E, SMB, SDE, CIPREL, ERANOVE).
          </p>
          <div className="inline-block mt-6 text-[11px] uppercase tracking-wide bg-ink-100 text-ink-600 px-3 py-1 rounded-sm font-semibold">
            Sprint 1 — CRUD à venir
          </div>
        </div>
      </main>
    </div>
  );
}
