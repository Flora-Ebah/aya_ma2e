/**
 * Kit de composants UI MA2E — design system GS2E/SARA.
 *
 * Basé sur les classes `.sa-*` (app/poc-design/sara.css) et les tokens GS2E
 * (vert/orange MA2E). Documentation complète : frontend/docs/design-kit.md.
 *
 *   import { PageHeader, Button, Card, DataTable } from "@/components/ui";
 */
export { Button, ButtonLink, buttonClass } from "./Button";
export type { ButtonVariant, ButtonSize } from "./Button";
export { IconButton } from "./IconButton";

export { Field, Input, Select, Textarea, Checkbox, Switch, FileInput, SearchInput, FormGrid, FormActions } from "./Field";
export { TextField } from "./TextField";

export { Card, CardHeader, ExpandableCard, KeyValueList } from "./Card";
export { Grid, KpiCard, Trend } from "./Grid";

export { Badge, StatusBadge, PriorityBadge, DeadlineBadge, deadlineFromDate, STATUS_MAP } from "./Badge";
export type { BadgeTone, Priority, DeadlineState } from "./Badge";
export { StatusPill } from "./StatusPill";

export { Tabs, TabPanel } from "./Tabs";
export type { TabItem } from "./Tabs";
export { Chip, ChipGroup, FilterBar } from "./Chip";

export { DataTable, RowActions } from "./DataTable";
export type { Column, SortState } from "./DataTable";
export { Pagination } from "./Pagination";
export { Popover, DropdownMenu } from "./Popover";
export type { MenuItem } from "./Popover";

export { Modal } from "./Modal";
export { Drawer } from "./Drawer";

export { PageHeader, Breadcrumb, DetailHeader, SectionTitle } from "./PageHeader";
export type { Crumb } from "./PageHeader";

export { EmptyState } from "./EmptyState";
export { Skeleton, SkeletonCard, SkeletonKpis } from "./Skeleton";
export { Spinner } from "./Spinner";
export { Toolbar } from "./Toolbar";
export { Tooltip } from "./Tooltip";
export { Avatar, initials } from "./Avatar";
export { Accordion } from "./Accordion";
export type { AccordionItem } from "./Accordion";
export { ProgressBar, Gauge } from "./Progress";
export { Alert } from "./Alert";
export type { AlertTone } from "./Alert";

// Toasts et confirmations : fournisseur global (déjà monté dans app/layout.tsx).
export { useToast, useConfirm } from "../ConfirmProvider";
export { Icon } from "../Icon";
export { cx } from "./util";
