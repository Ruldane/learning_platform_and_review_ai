/** Les trois fenêtres du rapport (jours locaux, aujourd'hui compris). */
export const COST_WINDOWS = [7, 30, 90] as const;
export type CostWindow = (typeof COST_WINDOWS)[number];

export interface CostTotalsView {
  calls: number;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  estimatedCalls: number;
}

/** Une ligne d'un tableau : `key` brut (jour, graphe, agent, modèle) et son libellé en français. */
export interface CostRowView extends CostTotalsView {
  key: string;
  label: string;
  /** La couleur de l'agent (jamais le seul signal : le nom est écrit). */
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
  /** L'écran du parcours, quand on en connaît un. */
  screenPath: string | null;
}
