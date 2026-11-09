import { StatusBadge } from "./Badge";

type Props = {
  status: string;
  label?: string;
};

/** @deprecated Alias historique — utiliser `StatusBadge`. */
export function StatusPill({ status, label }: Props) {
  return <StatusBadge status={status} label={label} />;
}
