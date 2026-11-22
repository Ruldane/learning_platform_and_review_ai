import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";
import { apiError } from "./councilHarness";

/** L'analyse d'une offre fictive telle que le back la rend (`PostingAnalysisOut`). */
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

/** Une offre (`PostingOut`) analysée par défaut. */
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

/** Une offre dont l'analyse tourne (session `a1`), sans titre ni fiche. */
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

/** Une ligne de la liste (`PostingSummaryOut`). */
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

/** Une ligne du tableau d'écarts (`GapRowOut`). */
export const gapRow = (skill: string, over: Record<string, unknown> = {}) => ({
  skill,
  required: false,
  level: null,
  action: "to_add",
  week: null,
  source: "posting",
  ...over,
});

/** L'écart d'une offre (`GapOut`) : Python à ajouter, SQL au programme, Go déjà validé. */
export const gapOut = (over: Record<string, unknown> = {}) => ({
  posting_id: "p1",
  status: "ready",
  score: 62,
  session_id: null,
  rows: [
    gapRow("Python", { required: true }),
    gapRow("Docker", { level: "declare" }),
    gapRow("SQL", { required: true, action: "in_program", week: 3 }),
    gapRow("Go", { level: "valide" }),
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
  /** Lectures successives de la liste ; la dernière se répète. */
  lists?: Record<string, unknown>[][];
  /** Lectures successives de `GET /postings/p1`. */
  postings?: Record<string, unknown>[];
  /** Lectures successives de `GET /postings/p1/gap`. */
  gaps?: Record<string, unknown>[];
  /** Remplace la lecture de la liste (une panne, par exemple). */
  list?: () => Response;
  /** Remplace la lecture de l'offre `p1` (404, panne). */
  posting?: () => Response;
  top?: () => Response;
  create?: Reply;
  plan?: Reply;
  remove?: Reply;
  relaunch?: Reply;
  distinct?: Reply;
  /** Réponse de `GET /applications/check` (sans fiche ni alerte par défaut). */
  check?: () => Response;
  /** Remplace la création de la candidature (`POST /applications`). */
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

/** Liste, création, lecture et suppression des offres. */
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

/** Écart, relance, ajout au planning et compétences les plus manquantes. */
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

/** La candidature de l'offre : la recherche de fiche existante et la création. */
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

/** `r1` : une replanification du programme `pg1` ; `a1` : l'analyse de l'offre. */
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
 * Les routes des offres et de l'écart. `state` garde les corps reçus (créations, ajouts au
 * planning, « distinctes ») et le nombre de lectures.
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

/** Un refus du back au format d'erreur (`code`, message français, détails). */
export const refusal = (status: number, code: string, message: string, details: unknown = null) =>
  HttpResponse.json(apiError(code, message, details), { status });
