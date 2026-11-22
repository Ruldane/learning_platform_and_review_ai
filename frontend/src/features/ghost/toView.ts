import type { components } from "@/shared/api/schema";
import type { Reference } from "./components/GhostComparison";

export function toReference(item: components["schemas"]["PracticeSummary"]): Reference {
  return {
    id: item.id,
    at: item.created_at,
    version: item.version,
    metrics: {
      duration: item.elapsed_ms,
      errors: item.errors,
      completed: item.progress,
      total: item.total,
      score: item.score_percent,
    },
  };
}
