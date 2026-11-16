import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { apiError } from "./councilHarness";

type Over = Record<string, unknown>;

/** Une compétence du classement (`TrendOut`) fictive. */
export const trendOut = (skill: string, rank: number, share: number, over: Over = {}) => ({
  skill,
  count: Math.round(share * 41),
  share,
  rank,
  delta_share: null,
  delta_rank: null,
  new: false,
  ...over,
});

/** Une offre lue (`OfferOut`) fictive. */
export const offerOut = (url: string, over: Over = {}) => ({
  url,
  title: "Data engineer",
  company: "Exemple Tech",
  level: "confirme",
  remote: null,
  salary: null,
  score: 78,
  ...over,
});

/** Un relevé complet (`RadarRunOut`) fictif : fini, 47 lues, 6 bloquées, 41 analysées. */
export const radarRun = (id: string, over: Over = {}) => ({
  id,
  role: "Data engineer",
  zone: "France",
  status: "done",
  trigger: "manual",
  created_at: "2026-11-16T09:00:00Z",
  finished_at: "2026-11-16T09:12:00Z",
  error_code: null,
  read_count: 47,
  blocked_count: 6,
  analyzed: 41,
  low_sample: false,
  not_postings: 0,
  not_analyzed: 0,
  blocked_domains: [{ domain: "example.invalid", count: 6 }],
  ranking: [trendOut("SQL", 1, 0.62, { delta_share: 8 }), trendOut("Python", 2, 0.5)],
  alerts: [],
  offers: [offerOut("https://example.org/jobs/1")],
  previous: null,
  ...over,
});

const SUMMARY_KEYS = [
  "id",
  "role",
  "zone",
  "status",
  "trigger",
  "created_at",
  "finished_at",
  "error_code",
  "read_count",
  "blocked_count",
  "analyzed",
  "low_sample",
];

/** `RadarRunSummary` : la forme courte d'un relevé, pour l'historique. */
const summaryOf = (run: Over) => Object.fromEntries(SUMMARY_KEYS.map((key) => [key, run[key]]));

export interface RadarApiOptions {
  /** Les relevés, le plus récent d'abord. */
  runs?: Over[];
  /** Poste et zone proposés. */
  defaults?: { role: string; zone: string };
  /** Les sessions de relevé connues du serveur (`GET /sessions`). */
  sessions?: Over[];
  /** Remplace la réponse de `POST /radar/runs` (un refus, un 409 particulier). */
  startReply?: () => Response;
}

interface RadarState {
  runs: Over[];
  defaults: { role: string; zone: string };
  sessions: Over[];
  bodies: Over[];
  startReply?: () => Response;
  latestReads: number;
  sessionReads: number;
  created: number;
}

/** Les lectures : `latest` suit les relevés (le plus récent fini est `latest`, un `running` est `running`). */
function readHandlers(state: RadarState) {
  return [
    http.get(`${API}/radar/latest`, () => {
      state.latestReads += 1;
      const running = state.runs.find((run) => run.status === "running");
      const latest = state.runs.find((run) => run.status !== "running");
      return HttpResponse.json({
        defaults: state.defaults,
        running: running ? { id: running.id, created_at: running.created_at } : null,
        latest: latest ?? null,
      });
    }),
    http.get(`${API}/radar/runs`, () => HttpResponse.json(state.runs.map(summaryOf))),
    http.get(`${API}/radar/runs/:id`, ({ params }) => {
      const run = state.runs.find((row) => row.id === params.id);
      return run
        ? HttpResponse.json(run)
        : HttpResponse.json(apiError("radar_run_not_found", "Relevé du radar introuvable."), {
            status: 404,
          });
    }),
    http.get(`${API}/sessions`, ({ request }) => {
      state.sessionReads += 1;
      const graph = new URL(request.url).searchParams.get("graph");
      return HttpResponse.json(state.sessions.filter((s) => !graph || s.graph === graph));
    }),
  ];
}

/**
 * Un relevé `running` tout neuf et sa session `sess-<id>`, donnée par le 202 seulement : elle
 * n'est pas dans `GET /sessions` (un test qui la lit autrement la retrouverait par hasard).
 */
function openRun(state: RadarState, body: Over): Response {
  state.created += 1;
  const id = `new${state.created}`;
  state.runs.unshift(
    radarRun(id, {
      role: String(body.role ?? state.defaults.role),
      zone: String(body.zone ?? state.defaults.zone),
      status: "running",
      finished_at: null,
      read_count: 0,
      blocked_count: 0,
      analyzed: 0,
      ranking: [],
      offers: [],
      blocked_domains: [],
    }),
  );
  return HttpResponse.json({ run_id: id, session_id: `sess-${id}` }, { status: 202 });
}

/** `POST /radar/runs` : refuse comme le serveur (un seul relevé en cours, un poste obligatoire). */
function startHandler(state: RadarState) {
  return http.post(`${API}/radar/runs`, async ({ request }) => {
    const body = ((await request.json().catch(() => null)) ?? {}) as Over;
    state.bodies.push(body);
    if (state.startReply) return state.startReply();
    const running = state.runs.find((run) => run.status === "running");
    if (running) {
      return HttpResponse.json(
        apiError("radar_in_progress", "Un relevé du radar est déjà en cours.", {
          run_id: running.id,
        }),
        { status: 409 },
      );
    }
    if (!String(body.role ?? state.defaults.role)) {
      return HttpResponse.json(
        apiError("radar_role_required", "Indique le poste visé pour lancer un relevé du radar."),
        { status: 409 },
      );
    }
    return openRun(state, body);
  });
}

/**
 * Le radar en mémoire : `bodies` garde les corps reçus, `runs` et `sessions` sont à la main du
 * test, `finish` clôt un relevé.
 */
export function radarApi(options: RadarApiOptions = {}) {
  const state: RadarState = {
    runs: [...(options.runs ?? [])],
    defaults: options.defaults ?? { role: "Data engineer", zone: "France" },
    sessions: [...(options.sessions ?? [])],
    bodies: [],
    startReply: options.startReply,
    latestReads: 0,
    sessionReads: 0,
    created: 0,
  };
  const finish = (id: string, over: Over = {}) => {
    state.runs = state.runs.map((run) =>
      run.id === id
        ? { ...run, status: "done", finished_at: "2026-11-16T10:00:00Z", ...over }
        : run,
    );
  };
  return { handlers: [...readHandlers(state), startHandler(state)], state, finish };
}

/** Les champs d'une session de relevé : le parcours et le sujet suivi (le relevé). */
export const radarSession = (runId: string): Over => ({
  graph: "market_radar",
  subject_type: "radar_run",
  subject_id: runId,
});
