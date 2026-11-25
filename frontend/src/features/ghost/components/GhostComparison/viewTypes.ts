/** Only aggregates are shown during the challenge. */
export interface Metrics {
  duration: number | null;
  errors: number | null;
  completed: number | null;
  total: number | null;
  score?: number | null;
}

export interface Reference {
  id: string;
  at: string;
  version: "same" | "changed" | "unknown";
  metrics: Metrics;
}
