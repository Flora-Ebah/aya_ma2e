import type { ReactNode } from "react";
import { PageHeader, type Crumb } from "@/components/ui";
import "./assistante.css";

export type { Crumb };

type Props = {
  crumbs: Crumb[];
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
};

/** En-tête de page GS2E : fil d'Ariane + titre Sora + description + actions (kit : PageHeader). */
export default function PageHead({ crumbs, title, description, actions }: Props) {
  return <PageHeader breadcrumb={crumbs} title={title} description={description} actions={actions} />;
}
