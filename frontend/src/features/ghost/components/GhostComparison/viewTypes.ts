/** Seuls des agrégats sont montrés pendant le défi. */
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
