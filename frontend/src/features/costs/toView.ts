import { playedLabel } from "@/shared/i18n/playedLabel";
import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import { graphLabel, graphScreen } from "./components/graphs";
import type { CallView, CostRowView, CostsView, CostTotalsView } from "./components/viewTypes";
import type { AgentCallOut, CostRow, CostsReport, CostTotals } from "./types";

const totals = (source: CostTotals): CostTotalsView => ({
  calls: source.calls,
  tokensIn: source.tokens_in,
  tokensOut: source.tokens_out,
  costUsd: source.cost_usd,
  estimatedCalls: source.estimated_calls,
});

function row(source: CostRow, label: string, color?: string): CostRowView {
  return { ...totals(source), key: source.key, label, color };
}

const modelLabel = (key: string) =>
  (key.startsWith("mcp:") ? playedLabel(key.slice(4)) : undefined) ?? key;

const plain = (source: CostRow) => row(source, source.key);
const byFeature = (source: CostRow) => row(source, graphLabel(source.key));

function byAgent(source: CostRow): CostRowView {
  if (source.key === "") return row(source, t("costs.noAgent"));
  const identity = agentIdentity(source.key);
  return row(source, identity.name, identity.color);
}

/**
 * The report: labels in French (« Hors session », named agents), unknown names kept raw.
 */
export function toCostsView(report: CostsReport): CostsView {
  return {
    days: report.days,
    since: report.since,
    until: report.until,
    total: totals(report.total),
    byDay: report.by_day.map(plain),
    byFeature: report.by_feature.map(byFeature),
    byAgent: report.by_agent.map(byAgent),
    byModel: report.by_model.map((r) => row(r, modelLabel(r.key))),
  };
}

/** A journal call, ready to display. */
export function toCallView(call: AgentCallOut): CallView {
  const identity = call.agent ? agentIdentity(call.agent) : null;
  return {
    id: call.id,
    at: call.at,
    agentLabel: identity?.name ?? t("costs.noAgent"),
    agentColor: identity?.color,
    graphLabel: graphLabel(call.graph),
    model: modelLabel(`${call.provider}:${call.model}`),
    tokensIn: call.tokens_in,
    tokensOut: call.tokens_out,
    latencyMs: call.latency_ms,
    costUsd: call.cost_usd,
    estimated: call.estimated,
    sessionId: call.session_id,
    screenPath: call.session_id ? graphScreen(call.graph) : null,
  };
}
