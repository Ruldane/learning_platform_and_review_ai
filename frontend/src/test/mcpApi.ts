import { delay, http, HttpResponse } from "msw";
import { API } from "./councilApi";

type Over = Record<string, unknown>;

/** Un jeton sans sa valeur (`McpTokenOut`). */
export const tokenOut = (over: Over = {}) => ({
  id: "tk1",
  label: "Claude Code (portable)",
  features: ["cv", "skills"],
  mode: "read",
  expires_at: "2099-12-10T12:00:00Z",
  revoked_at: null,
  last_used_at: null,
  created_at: "2026-11-10T12:00:00Z",
  ...over,
});

/** Une demande « À confirmer » (`McpConfirmationOut`), en attente par défaut. */
export const confirmationOut = (over: Over = {}) => ({
  id: "cf1",
  token_id: "tk1",
  action: "cv_master_profile_draft",
  summary: "Ajouter au profil maître : « Migration d'un entrepôt vers dbt ».",
  precheck: { ok: true, reasons: [], summary: "Tient face au profil." },
  status: "pending",
  expires_at: "2099-11-18T10:00:00Z",
  decided_at: null,
  created_at: "2026-11-17T10:00:00Z",
  ...over,
});

/** Les changements d'un appel de niveau 2 (`McpChangeOut`). */
export const changeOut = (over: Over = {}) => ({
  call_id: "call1",
  action: "skills_add_proof",
  rows: 2,
  tables: ["skill_proofs"],
  undone_at: null,
  created_at: "2026-11-17T09:00:00Z",
  ...over,
});

/** Une ligne du journal (`McpCallOut`). */
export const callRow = (over: Over = {}) => ({
  id: "call1",
  token_id: "tk1",
  action: "skills_add_proof",
  level: 2,
  code: 200,
  duration_ms: 84,
  ids: {},
  created_at: "2026-11-17T09:00:00Z",
  ...over,
});

/** Un outil exposé (`McpActionOut`). */
export const actionOut = (over: Over = {}) => ({
  name: "cv_list_documents",
  feature: "cv",
  kind: "route",
  route: "GET /cv/documents",
  level: 1,
  summary: "Liste les documents du CV.",
  side_effects: "db",
  untrusted: [],
  ...over,
});

export const FEATURES = [
  { feature: "cv", read_actions: 4, write_actions: 2, confirm_actions: 1 },
  { feature: "skills", read_actions: 3, write_actions: 1, confirm_actions: 0 },
  { feature: "postings", read_actions: 2, write_actions: 2, confirm_actions: 1 },
];

export const ACTIONS = [
  actionOut(),
  actionOut({
    name: "skills_add_proof",
    feature: "skills",
    level: 2,
    route: "POST /skills/proofs",
  }),
  actionOut({
    name: "postings_delete",
    feature: "postings",
    level: 3,
    route: "DELETE /postings/{id}",
    summary: "Supprime une offre.",
  }),
  actionOut({ name: "cv_review", feature: "cv", kind: "graph", route: null, level: 2 }),
];

interface McpApiOptions {
  enabled?: boolean;
  tokens?: Over[];
  confirmations?: Over[];
  changes?: Over[];
  calls?: Over[];
  actions?: Over[];
  /** Délai d'une décision (confirmer, refuser) : de quoi cliquer deux fois. */
  decideDelayMs?: number;
  /** Réponse d'une annulation refusée, au lieu de la réussite. */
  undoError?: { status: number; code: string; message: string };
}

interface McpState {
  enabled: boolean;
  tokens: Over[];
  confirmations: Over[];
  changes: Over[];
}

/** L'interrupteur et les jetons : ce qu'ils reçoivent est rangé dans `seen`. */
function tokenHandlers(
  state: McpState,
  seen: { created: Over[]; revoked: string[]; puts: boolean[] },
) {
  return [
    http.get(`${API}/mcp/settings`, () => HttpResponse.json({ enabled: state.enabled })),
    http.put(`${API}/mcp/settings`, async ({ request }) => {
      const body = (await request.json()) as { enabled: boolean };
      seen.puts.push(body.enabled);
      state.enabled = body.enabled;
      return HttpResponse.json({ enabled: state.enabled });
    }),
    http.get(`${API}/mcp/tokens`, () => HttpResponse.json(state.tokens)),
    http.post(`${API}/mcp/tokens`, async ({ request }) => {
      const body = (await request.json()) as Over;
      seen.created.push(body);
      const token = tokenOut({
        id: "tk-new",
        label: body.label,
        features: body.features,
        mode: body.mode,
      });
      state.tokens = [...state.tokens, token];
      return HttpResponse.json({ ...token, token: "tmcp_SECRET-VALUE-123" }, { status: 201 });
    }),
    http.delete(`${API}/mcp/tokens/:id`, ({ params }) => {
      seen.revoked.push(String(params.id));
      state.tokens = state.tokens.map((token) =>
        token.id === params.id ? { ...token, revoked_at: "2026-11-17T12:00:00Z" } : token,
      );
      return new HttpResponse(null, { status: 204 });
    }),
  ];
}

/** Les demandes à confirmer : confirmer ou refuser change leur état, comme le vrai serveur. */
function confirmationHandlers(state: McpState, decisions: string[], delayMs?: number) {
  return [
    http.get(`${API}/mcp/confirmations`, () => HttpResponse.json(state.confirmations)),
    ...(["confirm", "refuse"] as const).map((decision) =>
      http.post(`${API}/mcp/confirmations/:id/${decision}`, async ({ params }) => {
        decisions.push(`${decision}:${String(params.id)}`);
        if (delayMs) await delay(delayMs);
        const status = decision === "confirm" ? "confirmed" : "refused";
        state.confirmations = state.confirmations.map((item) =>
          item.id === params.id ? { ...item, status } : item,
        );
        return HttpResponse.json(state.confirmations.find((item) => item.id === params.id));
      }),
    ),
  ];
}

/**
 * Faux serveur de l'accès MCP, avec un petit état (jetons, interrupteur, demandes, changements) ;
 * garde ce qu'il reçoit pour vérifier combien de requêtes sont parties et avec quel corps.
 */
export function mcpApi(options: McpApiOptions = {}) {
  const state: McpState = {
    enabled: options.enabled ?? true,
    tokens: [...(options.tokens ?? [tokenOut()])],
    confirmations: [...(options.confirmations ?? [confirmationOut()])],
    changes: [...(options.changes ?? [changeOut()])],
  };
  const created: Over[] = [];
  const decisions: string[] = [];
  const undone: string[] = [];
  const settingsPuts: boolean[] = [];
  const revoked: string[] = [];
  const handlers = [
    ...tokenHandlers(state, { created, revoked, puts: settingsPuts }),
    ...confirmationHandlers(state, decisions, options.decideDelayMs),
    http.get(`${API}/mcp/features`, () => HttpResponse.json(FEATURES)),
    http.get(`${API}/mcp/actions`, () => HttpResponse.json(options.actions ?? ACTIONS)),
    http.get(`${API}/mcp/calls`, () => HttpResponse.json(options.calls ?? [callRow()])),
    http.get(`${API}/mcp/changes`, () => HttpResponse.json(state.changes)),
    http.post(`${API}/mcp/changes/:id/undo`, ({ params }) => {
      if (options.undoError) {
        const { status, code, message } = options.undoError;
        return HttpResponse.json({ error: { code, message, details: null } }, { status });
      }
      undone.push(String(params.id));
      state.changes = state.changes.map((item) =>
        item.call_id === params.id ? { ...item, undone_at: "2026-11-17T12:00:00Z" } : item,
      );
      return HttpResponse.json({ call_id: params.id, undone: 2 });
    }),
  ];
  return { handlers, state, created, decisions, undone, settingsPuts, revoked };
}
