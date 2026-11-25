import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { apiError } from "./councilHarness";

type Over = Record<string, unknown>;

/** A fake ranking skill (`TrendOut`). */
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
  level: "mid_level",
  remote: null,
  salary: null,
  score: 78,
  ...over,
});

/** A fake complete scan (`RadarRunOut`): finished, 47 read, 6 blocked, 41 analysed. */
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
  "not_postings",
  "blocked_count",
  "analyzed",
  "low_sample",
];

/** `RadarRunSummary`: the short shape of a scan, for the history. */
const summaryOf = (run: Over) => Object.fromEntries(SUMMARY_KEYS.map((key) => [key, run[key]]));

export interface RadarApiOptions {
  /** Scans, most recent first. */
  runs?: Over[];
  /** Suggested role and area. */
  defaults?: { role: string; zone: string };
  /** Scan sessions known to the server (`GET /sessions`). */
  sessions?: Over[];
  /** Overrides the response of `POST /radar/runs` (a refusal, a specific 409). */
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

/** Reads: `latest` follows the scans (latest finished one; a `running` one stays `running`). */
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
 * A brand-new `running` scan and its session `sess-<id>`, given only by the 202: it is
 * not in `GET /sessions` (a test reading it another way would find it by chance).
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

/** `POST /radar/runs`: refuses like the server (one scan at a time, a role required). */
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
 * The radar in memory: `bodies` keeps the bodies received, `runs` and `sessions` are the
 * test's to edit, `finish` closes a scan.
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

/** The fields of a scan session: the course and the tracked subject (the scan). */
export const radarSession = (runId: string): Over => ({
  graph: "market_radar",
  subject_type: "radar_run",
  subject_id: runId,
});
