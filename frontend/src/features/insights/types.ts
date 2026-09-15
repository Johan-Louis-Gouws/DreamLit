import type { InsightRecord } from "../../types";

export type AnswerData = {
  question: string;
  answer: string;
  topic: string;
  scope: "ongoing" | "current" | "dream";
  status: "current" | "changed" | "excluded";
  dream_id: string | null;
  person_id: string | null;
  audio_id: string | null;
};

export type PersonData = {
  name: string;
  aliases: string[];
  relationship: string;
  notes: string;
  include_in_analysis: boolean;
};

export type InvestigationData = {
  question: string;
  notes: string;
  conclusion: string;
  status: "open" | "resolved" | "archived";
  dream_ids: string[];
};

export type ExperimentData = {
  action: string;
  intention: string;
  outcome: string;
  due_on: string | null;
  status: "planned" | "active" | "completed" | "dropped";
  investigation_id: string | null;
  person_id: string | null;
};

export type AnswerRecord = InsightRecord<AnswerData>;
export type PersonRecord = InsightRecord<PersonData>;
export type InvestigationRecord = InsightRecord<InvestigationData>;
export type ExperimentRecord = InsightRecord<ExperimentData>;
