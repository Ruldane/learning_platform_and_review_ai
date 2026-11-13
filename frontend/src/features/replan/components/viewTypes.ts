import type { PlanDiffView } from "@/shared/session-ui";

export type VersionKind = "build" | "replan";
export type VersionStatus =
  "accepted" | "pending" | "refused" | "superseded" | "empty" | "impossible";

/** La charge d'une semaine avant et après la proposition, en minutes, sous son plafond. */
export interface WeekLoadView {
  rank: number;
  /** Lundi de la semaine, `AAAA-MM-JJ`. */
  startDate: string;
  before: number;
  after: number;
  cap: number;
}

/** Une version du plan, telle que l'historique la montre. */
export interface VersionView {
  version: number;
  kind: VersionKind;
  status: VersionStatus;
  reason: string;
  /** Instant ISO de la création. */
  createdAt: string;
  /** Texte du bilan hebdomadaire qui a déclenché la version, ou `null`. */
  review: string | null;
  diff: PlanDiffView | null;
  /** Durée du programme en semaines avant et après la version ; `null` sans diff. */
  weeks: { before: number; after: number } | null;
  weekLoads: WeekLoadView[];
  /** La session de replanification qui a produit la version, ou `null`. */
  sessionId: string | null;
}
