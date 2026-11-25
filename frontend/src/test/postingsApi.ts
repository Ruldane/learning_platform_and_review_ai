import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";
import { apiError } from "./councilHarness";

/** The analysis of a fake job posting as the back returns it (`PostingAnalysisOut`). */
export const analysisOut = (over: Record<string, unknown> = {}) => ({
  title: "Ingénieure données",
  company: "Société Fictive",
  level: "senior",
  location: "Lyon",
  remote: "partiel",
  language: "fr",
  apply_url: null,
  requirements: [
    { text: "Python solide", required: true, skills: ["Python"] },
    { text: "Docker apprécié", required: false, skills: ["Docker"] },
  ],
  keywords: [{ term: "Airflow", variants: [] }],
  eliminatory: [{ kind: "language", text: "Anglais courant" }],
  skills: [
    { name: "Python", domain: "données", required: true, learnable: true },
    { name: "Docker", domain: "outils", required: false, learnable: true },
  ],
  tools: ["Airflow"],
  ...over,
});

/** A posting (`PostingOut`) analysed by default. */
export const postingOut = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  status: "ready",
  source: "url",
  url: "https://example.org/jobs/1",
  text: "",
  title: "Ingénieure données",
  company: "Société Fictive",
  score: 62,
  has_review: false,
  gap_session_id: null,
  failure_reason: null,
  created_at: "2026-11-03T10:00:00Z",
  duplicates: [],
  analysis: analysisOut(),
  ...over,
});

/** A posting whose analysis is running (session `a1`), with no title or record. */
export const analyzingPosting = (over: Record<string, unknown> = {}) =>
  postingOut({
    status: "analyzing",
    title: null,
    company: null,
    score: null,
    analysis: null,
    gap_session_id: "a1",
    ...over,
  });

/** A list row (`PostingSummaryOut`). */
export const summaryOut = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  status: "ready",
  source: "url",
  title: "Ingénieure données",
  company: "Société Fictive",
  score: 62,
  has_review: false,
  created_at: "2026-11-03T10:00:00Z",
  ...over,
});

/** A gap table row (`GapRowOut`). */
export const gapRow = (skill: string, over: Record<string, unknown> = {}) => ({
  skill,
  required: false,
  level: null,
  action: "to_add",
  week: null,
  source: "posting",
  ...over,
});

/** A posting's gap (`GapOut`): Python to add, SQL in the program, Go already validated. */
export const gapOut = (over: Record<string, unknown> = {}) => ({
  posting_id: "p1",
  status: "ready",
  score: 62,
  session_id: null,
  rows: [
    gapRow("Python", { required: true }),
    gapRow("Docker", { level: "declared" }),
    gapRow("SQL", { required: true, action: "in_program", week: 3 }),
    gapRow("Go", { level: "validated" }),
  ],
  ...over,
});

export const topMissing = () => [
  { skill: "Python", postings: 5, required_in: 4 },
  { skill: "Docker", postings: 1, required_in: 0 },
];

type Reply = (request: Request) => Response | Promise<Response>;

interface PostingsApi {
  programs?: Record<string, unknown>[];
  /** Successive reads of the list; the last one repeats. */
  lists?: Record<string, unknown>[][];
  /** Successive reads of `GET /postings/p1`. */
  postings?: Record<string, unknown>[];
  /** Successive reads of `GET /postings/p1/gap`. */
  gaps?: Record<string, unknown>[];
  /** Overrides reading the list (a failure, for example). */
  list?: () => Response;
  /** Overrides reading posting `p1` (404, failure). */
  posting?: () => Response;
  top?: () => Response;
  create?: Reply;
  plan?: Reply;
  remove?: Reply;
  relaunch?: Reply;
  distinct?: Reply;
  /** Response of `GET /applications/check` (no record or alert by default). */
  check?: () => Response;
  /** Overrides creating the application (`POST /applications`). */
  application?: Reply;
}

const at = <T>(items: T[], index: number): T => items[Math.min(index, items.length - 1)]!;

type State = ReturnType<typeof newState>;

const newState = () => ({
  created: [] as unknown[],
  plans: [] as unknown[],
  planSources: [] as (string | null)[],
  distincts: [] as unknown[],
  applications: [] as unknown[],
  checks: [] as string[],
  removed: 0,
  relaunched: 0,
  reads: { list: 0, posting: 0, gap: 0 },
});

/** List, create, read and delete postings. */
function postingRoutes(api: PostingsApi, state: State) {
  const lists = api.lists ?? [[summaryOut()]];
  const postings = api.postings ?? [postingOut()];
  return [
    http.get(
      `${API}/postings`,
      () => api.list?.() ?? HttpResponse.json(at(lists, state.reads.list++)),
    ),
    http.post(`${API}/postings`, async ({ request }) => {
      state.created.push(await request.clone().json());
      if (api.create) return api.create(request);
      return HttpResponse.json(
        { created: true, posting: postingOut({ id: "p9", status: "analyzing" }), session_id: "a1" },
        { status: 201 },
      );
    }),
    http.get(
      `${API}/postings/p1`,
      () => api.posting?.() ?? HttpResponse.json(at(postings, state.reads.posting++)),
    ),
    http.delete(`${API}/postings/p1`, ({ request }) => {
      state.removed += 1;
      return api.remove?.(request) ?? new HttpResponse(null, { status: 204 });
    }),
    http.post(`${API}/postings/p1/distinct`, async ({ request }) => {
      state.distincts.push(await request.clone().json());
      return api.distinct?.(request) ?? new HttpResponse(null, { status: 204 });
    }),
  ];
}

/** Gap, follow-up, planning addition and the most missing skills. */
function gapRoutes(api: PostingsApi, state: State) {
  const gaps = api.gaps ?? [gapOut()];
  return [
    http.get(`${API}/programs`, () => HttpResponse.json(api.programs ?? [])),
    http.get(`${API}/cv/versions`, () => HttpResponse.json([])),
    http.get(`${API}/postings/p1/gap`, () => HttpResponse.json(at(gaps, state.reads.gap++))),
    http.post(`${API}/postings/p1/gap`, ({ request }) => {
      state.relaunched += 1;
      return api.relaunch?.(request) ?? HttpResponse.json({ session_id: "a2" }, { status: 202 });
    }),
    http.post(`${API}/postings/p1/gap/plan`, async ({ request }) => {
      state.plans.push(await request.clone().json());
      state.planSources.push(request.headers.get("X-Tremplin-Run"));
      return api.plan?.(request) ?? HttpResponse.json({ session_id: "r1" }, { status: 202 });
    }),
    http.get(`${API}/gap/top-missing`, () => api.top?.() ?? HttpResponse.json(topMissing())),
  ];
}

/** The posting's application: existing-record search and creation. */
function applicationRoutes(api: PostingsApi, state: State) {
  return [
    http.get(`${API}/applications/check`, ({ request }) => {
      state.checks.push(new URL(request.url).search);
      return api.check?.() ?? HttpResponse.json({ own: null, alerts: [], info: [] });
    }),
    http.post(`${API}/applications`, async ({ request }) => {
      state.applications.push(await request.clone().json());
      if (api.application) return api.application(request);
      return HttpResponse.json(
        {
          application: { id: "ap1", company: "Société Fictive", title: "Ingénieure données" },
          info: [],
        },
        { status: 201 },
      );
    }),
  ];
}

/** `r1`: a replanning of program `pg1`; `a1`: the posting's analysis. */
const sessionRoutes = () => [
  http.get(`${API}/sessions/r1`, () =>
    HttpResponse.json(
      sessionOut("r1", "running", { graph: "replan", subject_type: "program", subject_id: "pg1" }),
    ),
  ),
  http.get(`${API}/sessions/a1`, () =>
    HttpResponse.json(
      sessionOut("a1", "running", { graph: "gap_analysis", subject_type: "posting" }),
    ),
  ),
];

/**
 * The posting and gap routes. `state` keeps the bodies received (creations, additions to the
 * planning, « distinctes ») and the number of reads.
 */
export function postingsApi(api: PostingsApi = {}) {
  const state = newState();
  const handlers = [
    ...postingRoutes(api, state),
    ...gapRoutes(api, state),
    ...applicationRoutes(api, state),
    ...sessionRoutes(),
  ];
  return { state, handlers };
}

/** A back refusal in the error format (`code`, French message, details). */
export const refusal = (status: number, code: string, message: string, details: unknown = null) =>
  HttpResponse.json(apiError(code, message, details), { status });
