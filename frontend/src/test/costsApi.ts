import { http, HttpResponse } from "msw";
import { addDays } from "@/shared/lib/format";
import { API } from "./councilApi";

/** Une ligne du rapport des coûts (`CostRow`). */
export const costRow = (key: string, over: Record<string, unknown> = {}) => ({
  key,
  calls: 3,
  tokens_in: 1200,
  tokens_out: 340,
  cost_usd: 0.12,
  estimated_calls: 0,
  ...over,
});

const UNTIL = "2026-11-16";

/**
 * Un rapport (`CostsReport`) sur `days` jours finissant le 16 novembre 2026 : trois jours d'appels,
 * les autres à zéro ; quatre features (dont « hors session » et un graphe inconnu), trois agents
 * (dont un inconnu), deux modèles.
 */
export function costsReport(days = 30, over: Record<string, unknown> = {}) {
  const since = addDays(UNTIL, 1 - days);
  const byDay = Array.from({ length: days }, (_, index) => {
    const key = addDays(since, index);
    const last = index >= days - 3;
    return last
      ? costRow(key, { calls: 4, tokens_in: 1600, tokens_out: 453, cost_usd: 0.14 })
      : costRow(key, { calls: 0, tokens_in: 0, tokens_out: 0, cost_usd: 0 });
  });
  return {
    days,
    since,
    until: UNTIL,
    total: { calls: 12, tokens_in: 4800, tokens_out: 1360, cost_usd: 0.42, estimated_calls: 3 },
    by_day: byDay,
    by_feature: [
      costRow("learning_council", { calls: 5, cost_usd: 0.2 }),
      costRow("", { calls: 4, cost_usd: 0.1 }),
      costRow("mystery_graph", { calls: 2, cost_usd: 0.08 }),
      costRow("quiz", { calls: 1, cost_usd: 0.04, estimated_calls: 1 }),
    ],
    by_agent: [
      costRow("strategist", { calls: 6, cost_usd: 0.25 }),
      costRow("ghost_agent", { calls: 3, cost_usd: 0.12 }),
      costRow("", { calls: 3, cost_usd: 0.05, estimated_calls: 3 }),
    ],
    by_model: [
      costRow("glm:glm-5.3-flash", { calls: 9, cost_usd: 0.3 }),
      costRow("ollama:qwen3", { calls: 3, cost_usd: 0 }),
    ],
    ...over,
  };
}

/** Un appel du journal (`AgentCallOut`). */
export const callOut = (id: string, over: Record<string, unknown> = {}) => ({
  id,
  at: "2026-11-16T09:30:00Z",
  session_id: "sess-1234567890",
  graph: "learning_council",
  agent: "strategist",
  provider: "glm",
  model: "glm-5.3-flash",
  tokens_in: 1200,
  tokens_out: 340,
  latency_ms: 1840,
  cost_usd: 0.0123,
  estimated: false,
  ...over,
});

export const FIRST_CURSOR = "cursor-1";

/**
 * Les pages du journal : sans `before`, la première ; avec `FIRST_CURSOR`, la seconde ; un filtre,
 * une page seule.
 */
export function callPage(url: URL) {
  if (url.searchParams.get("agent") || url.searchParams.get("graph")) {
    return { items: [callOut("c-filtered", { agent: "scribe" })], next_before: null };
  }
  if (url.searchParams.get("before") === FIRST_CURSOR) {
    return {
      items: [callOut("c3", { graph: null, session_id: null, agent: null })],
      next_before: null,
    };
  }
  return {
    items: [
      callOut("c1"),
      callOut("c2", { graph: "mystery_graph", agent: "ghost_agent", estimated: true }),
    ],
    next_before: FIRST_CURSOR,
  };
}

interface CostsApiOptions {
  /** `GET /costs` : le rapport (défaut `costsReport(days)`) ou une réponse brute. */
  report?: (days: number) => object | Response;
  /** `GET /costs/calls` : la page (défaut `callPage`) ou une réponse brute. */
  calls?: (url: URL) => object | Response;
}

const reply = (value: object | Response) =>
  value instanceof Response ? value : HttpResponse.json(value);

/**
 * Faux serveur des coûts et du journal ; garde les adresses reçues pour vérifier les paramètres.
 */
export function costsApi(options: CostsApiOptions = {}) {
  const costRequests: URL[] = [];
  const callRequests: URL[] = [];
  const handlers = [
    http.get(`${API}/costs`, ({ request }) => {
      const url = new URL(request.url);
      costRequests.push(url);
      const days = Number(url.searchParams.get("days") ?? 30);
      return reply(options.report?.(days) ?? costsReport(days));
    }),
    http.get(`${API}/costs/calls`, ({ request }) => {
      const url = new URL(request.url);
      callRequests.push(url);
      return reply(options.calls?.(url) ?? callPage(url));
    }),
  ];
  return { handlers, costRequests, callRequests };
}
