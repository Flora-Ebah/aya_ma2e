export type KPIDelta = {
  current: number;
  previous: number;
  delta: number;
  delta_pct: number | null;
};

export type KpiAlert = {
  kpi: string;
  value: number;
  threshold: number;
  op: string;
  severity: "warning" | "danger";
};

export type Overview = {
  period_days: number;
  total_dossiers: number;
  total_period: number;
  submitted: number;
  validated: number;
  rejected: number;
  complement_requested: number;
  in_progress: number;
  validation_rate: number;
  avg_validation_hours: number | null;
  auto_complete_rate: number;
  total_conversations: number;
  total_messages: number;
  deltas?: Record<string, KPIDelta> | null;
  alerts?: KpiAlert[] | null;
};

export type TimelinePoint = { date: string; created: number; validated: number; rejected: number };

export type ChannelStat = { channel: string; dossiers: number; conversations: number; share_pct: number };

export type RejectionReason = { motive: string; count: number; share_pct: number };

export type AgentPerf = {
  agent_id: string;
  agent_name: string;
  validated: number;
  rejected: number;
  complement_requested: number;
  total_decisions: number;
};

export type OcrQuality = {
  average_confidence: number | null;
  high_quality_pct: number;
  medium_quality_pct: number;
  low_quality_pct: number;
  total_pieces: number;
};

export type Funnel = {
  conversations_started: number;
  dossiers_created: number;
  dossiers_submitted: number;
  dossiers_validated: number;
  started_to_created_pct: number;
  created_to_submitted_pct: number;
  submitted_to_validated_pct: number;
  overall_pct: number;
};
