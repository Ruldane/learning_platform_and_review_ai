import type { CostWindow } from "./components/viewTypes";

/** Clés TanStack Query de la feature : la fenêtre et les filtres, jamais une donnée du journal. */
export const costsKeys = {
  report: (days: CostWindow) => ["costs", "report", days] as const,
  calls: (agent: string | null, graph: string | null) =>
    ["costs", "calls", agent ?? "all", graph ?? "all"] as const,
} as const;
