export interface Vacancy {
  id: number;
  client_id: number;
  title: string;
  scenario_name: string;
  pass_score: number;
  active: boolean;
  created_at: string;
}

export interface VacancyReport {
  vacancy_id: number;
  title: string;
  candidates_total: number;
  calls_total: number;
  calls_with_score: number;
  by_decision: Record<string, number>;
  avg_score: number | null;
}

export interface CandidateBrief {
  id: number;
  fio: string;
  phone: string;
  vacancy_id: number;
}

export interface Call {
  id: number;
  candidate_id: number;
  candidate: CandidateBrief | null;
  voximplant_call_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration: number | null;
  score: number | null;
  decision: string | null;
  score_reasoning: string | null;
  answers: Record<string, string> | null;
  attempt: number;
  has_recording: boolean;
}

export interface CallTurn {
  order: number;
  speaker: "agent" | "candidate" | string;
  text: string;
}

export interface CallDetail extends Call {
  turns: CallTurn[];
  transcript: string | null;
}

export interface CallsList {
  items: Call[];
  limit: number;
  offset: number;
}

export interface UploadResult {
  vacancy_id: number;
  created: number;
  duplicates: number;
  invalid: { row: number; reason: string }[];
  enqueued: number;
}

export interface CandidateRow {
  id: number;
  vacancy_id: number;
  fio: string;
  phone: string;
  source: string | null;
  status: string;
  created_at: string;
  last_call: {
    id: number;
    started_at: string | null;
    score: number | null;
    decision: string | null;
  } | null;
}

export interface CandidatesList {
  items: CandidateRow[];
  vacancy_id: number;
}

export interface CallEnqueued {
  candidate_id: number;
  task_id: string;
}
