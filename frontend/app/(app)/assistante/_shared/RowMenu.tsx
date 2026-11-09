"use client";
import { DropdownMenu } from "@/components/ui";

export type RowMenuItem = {
  label: string;
  icon?: string;
  danger?: boolean;
  disabled?: boolean;
  onSelect: () => void;
};

/** Menu « ⋯ » d'actions secondaires d'une ligne ou d'une carte (kit : DropdownMenu). */
export default function RowMenu({ items, label = "Autres actions" }: { items: RowMenuItem[]; label?: string }) {
  return (
    <DropdownMenu
      label={label}
      items={items.map((it) => ({
        label: it.label, icon: it.icon, danger: it.danger, disabled: it.disabled, onClick: it.onSelect,
      }))}
    />
  );
}
