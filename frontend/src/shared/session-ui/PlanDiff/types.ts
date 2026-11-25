/** View types for a program diff: independent of the API contract (D34). */

export interface PlanDiffTask {
  id: string;
  title: string;
  moduleTitle: string;
  /** Planned day; `null` when no longer known (task removed). */
  plannedDate: string | null;
}

export interface PlanDiffMove {
  id: string;
  title: string;
  moduleTitle: string;
  from: string;
  to: string;
}

export interface PlanDiffView {
  added: PlanDiffTask[];
  removed: PlanDiffTask[];
  moved: PlanDiffMove[];
}
