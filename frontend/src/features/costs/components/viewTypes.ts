/** The three report windows (local days, today included). */
export const COST_WINDOWS = [7, 30, 90] as const;
export type CostWindow = (typeof COST_WINDOWS)[number];

export interface CostTotalsView {
  calls: number;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  estimatedCalls: number;
}

/** A table row: the raw `key` (day, graph, agent, model) and its French label. */
export interface CostRowView extends CostTotalsView {
  key: string;
  label: string;
  /** The agent's colour (never the only signal: the name is written too). */
  color?: string;
}

export interface CostsView {
  days: number;
  since: string;
  until: string;
  total: CostTotalsView;
  byDay: CostRowView[];
  byFeature: CostRowView[];
  byAgent: CostRowView[];
  byModel: CostRowView[];
}

export interface CallView {
  id: string;
  at: string;
  agentLabel: string;
  agentColor?: string;
  graphLabel: string;
  model: string;
  tokensIn: number;
  tokensOut: number;
  latencyMs: number;
  costUsd: number;
  estimated: boolean;
  sessionId: string | null;
  /** The graph's screen, when one is known. */
  screenPath: string | null;
}
