export type Provider = "codex" | "claude";
export interface Dream {
  id: string;
  dreamed_on: string;
  text: string;
  context: string;
  revision: number;
  audio_id: string | null;
  created_at: string;
}
export interface Job {
  id: string;
  kind: string;
  provider: Provider | null;
  state: "queued" | "running" | "completed" | "failed" | "cancelled";
  stage: string;
  error_code: string | null;
  result_id: string | null;
}
export interface Evidence {
  dream_id: string;
  revision: number;
  field: "text" | "context";
  quote: string;
}
export interface Pattern {
  id: string;
  analysis_id: string;
  title: string;
  observation: string;
  hypothesis: string | null;
  question: string;
  alternatives: string[];
  evidence: Evidence[];
  counterevidence?: Evidence[];
  provider?: Provider;
  stale?: boolean;
  feedback?: { verdict: string; note: string }[];
  reflections?: {
    id: string;
    provider: Provider;
    message: string;
    stale?: boolean;
    personal_context_sources?: PersonalContextSource[];
    output: { response: string; evidence: Evidence[] };
  }[];
}
export interface Analysis {
  id: string;
  provider: Provider;
  model: string | null;
  stale: boolean;
  output: {
    summary: string;
    observations: {
      kind: string;
      label: string;
      inferred: boolean;
      evidence: Evidence[];
    }[];
  };
  patterns: Pattern[];
  scope: {
    included_dream_ids: string[];
    total_eligible_dreams: number;
    truncated: boolean;
  };
  personal_context_sources?: PersonalContextSource[];
}

export type RecordKind = "answer" | "person" | "investigation" | "experiment";
export type RunKind =
  "question" | "turning_points" | "investigation" | "portrait" | "weekly";

export interface InsightRecord<
  T extends Record<string, unknown> = Record<string, unknown>,
> {
  id: string;
  kind: RecordKind;
  revision: number;
  data: T;
  created_at: string;
  updated_at: string;
}

export interface PersonalContextSource {
  kind: RecordKind;
  id: string;
  revision: number;
  label: string;
}

export interface InsightSource {
  kind: "dream" | RecordKind;
  id: string;
  revision: number;
  date: string;
  label: string;
  fields: Record<string, string>;
}

export interface InsightEvidence {
  source_kind: InsightSource["kind"];
  source_id: string;
  revision: number;
  field: string;
  quote: string;
}

export interface InsightOutput {
  title: string;
  summary: string;
  sections: {
    heading: string;
    body: string;
    evidence: InsightEvidence[];
    counterevidence: InsightEvidence[];
  }[];
  question: string;
}

export interface InsightRun {
  id: string;
  kind: RunKind;
  subject_id: string | null;
  provider: Provider;
  model: string | null;
  output: InsightOutput;
  sources: InsightSource[];
  scope: {
    included_dream_ids: string[];
    total_eligible_dreams: number;
    truncated: boolean;
    date_from: string | null;
    date_to: string | null;
  };
  stale: boolean;
  created_at: string;
}
export interface Preferences {
  provider: Provider;
  codex_model: string;
  claude_model: string;
  whisper_binary: string;
  whisper_model: string;
  ffmpeg_binary: string;
}
export interface GraphNode {
  id: string;
  label: string;
  kind: string;
  dream_id: string | null;
  pattern_id: string | null;
  date?: string;
  evidence?: Evidence[];
}
export interface GraphData {
  nodes: GraphNode[];
  edges: {
    id: string;
    source: string;
    target: string;
    kind: string;
    analysis_id: string;
  }[];
  scope: {
    included_dream_ids: string[];
    total_eligible_dreams: number;
    truncated: boolean;
  };
}
export interface Association {
  id: string;
  label: string;
  meaning: string;
  dream_id: string | null;
}
