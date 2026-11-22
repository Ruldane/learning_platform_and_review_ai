import { apiBaseUrl } from "@/shared/api/client";
import type { BlindRun } from "./api";
import type { VerdictView } from "./components/viewTypes";

export function toVerdict(run: BlindRun): VerdictView | null {
  const result = run.result;
  if (!result) return null;
  const base = apiBaseUrl.replace(/\/$/, "");
  return {
    winner: result.verdict,
    feedback: result.feedback,
    scores: run.rubric.criteria.map((criterion, idx) => ({
      label: criterion.label,
      a: result.scores_a[idx] ?? null,
      b: result.scores_b[idx] ?? null,
    })),
    linkA: { href: base + result.source_a.url, label: result.source_a.label },
    linkB: { href: base + result.source_b.url, label: result.source_b.label },
  };
}
