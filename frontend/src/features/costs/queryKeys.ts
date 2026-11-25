import type { CostWindow } from "./components/viewTypes";

/** TanStack Query keys of the feature: the window and the filters, never a journal entry. */
export const costsKeys = {
  report: (days: CostWindow) => ["costs", "report", days] as const,
  calls: (agent: string | null, graph: string | null) =>
    ["costs", "calls", agent ?? "all", graph ?? "all"] as const,
} as const;
