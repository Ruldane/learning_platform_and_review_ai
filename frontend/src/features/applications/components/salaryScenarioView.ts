export interface SalaryScenarioView {
  runId: string;
  role: string;
  zone: string;
  minimum: number;
  maximum: number;
  observations: number;
  outcome: {
    offer: number;
    remaining: number;
    reason: "ceiling_reached" | "budget_held" | "fixed_amount";
  } | null;
}
