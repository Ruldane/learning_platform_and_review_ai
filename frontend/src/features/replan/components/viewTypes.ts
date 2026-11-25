import type { PlanDiffView } from "@/shared/session-ui";

export type VersionKind = "build" | "replan";
export type VersionStatus =
  "accepted" | "pending" | "refused" | "superseded" | "empty" | "impossible";

/** A week's load before and after the proposal, in minutes, under its cap. */
export interface WeekLoadView {
  rank: number;
  /** Monday of the week, `YYYY-MM-DD`. */
  startDate: string;
  before: number;
  after: number;
  cap: number;
}

/** A plan version, as the history shows it. */
export interface VersionView {
  version: number;
  kind: VersionKind;
  status: VersionStatus;
  reason: string;
  /** ISO instant of the creation. */
  createdAt: string;
  /** Text of the weekly review that triggered the version, or `null`. */
  review: string | null;
  diff: PlanDiffView | null;
  /** Program length in weeks before and after the version; `null` without a diff. */
  weeks: { before: number; after: number } | null;
  weekLoads: WeekLoadView[];
  /** The replan session that produced the version, or `null`. */
  sessionId: string | null;
}
