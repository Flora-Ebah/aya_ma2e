"use client";
import AuthGuard from "@/components/AuthGuard";
import AppShell from "@/components/AppShell";

/**
 * Layout du back-office — coque .sa-app du design system GS2E (sidebar à
 * groupes repliables, header 56 px, barre basse mobile). Voir AppShell.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
