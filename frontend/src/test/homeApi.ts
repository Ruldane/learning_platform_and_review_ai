import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";
import { apiError } from "./councilHarness";

type Over = Record<string, unknown>;

const blockRubric = {
  lesson_id: "l1",
  lesson_title: "Les jointures SQL",
  module_title: "SQL pour l'analyse",
  minutes: 90,
  tasks: [
    { title: "Lire la leçon", minutes: 30 },
    { title: "Faire le quiz", minutes: 60 },
  ],
};

const remindersRubric = {
  due: 2,
  items: [
    {
      reminder_id: "r1",
      application_id: "a1",
      company: "Société Fictive",
      title: "Data engineer",
      due_on: "2026-11-16",
      kind: "linkedin_7",
    },
  ],
};

const offersRubric = {
  run_id: "run1",
  items: [
    {
      title: "Analytics engineer",
      company: "Exemple Tech",
      score: 78,
      url: "https://example.org/jobs/ae",
    },
  ],
};

const weekRubric = {
  done_minutes: 190,
  planned_minutes: 300,
  streak_days: 4,
  study_minutes: 190,
  tasks_done: 3,
  tasks_total: 8,
};

const resourceRubric = {
  title: "Comprendre les index",
  domain: "example.org",
  published: "2026-11-10",
  why: "Tu travailles les jointures cette semaine.",
  url: "https://example.org/index",
};

/** A full brief (`BriefOut`), fake: all seven sections filled, the advice ready. */
export const briefOut = (over: Over = {}) => ({
  id: "b1",
  day: "2026-11-16",
  generated_at: "2026-11-16T06:00:00Z",
  origin: "schedule",
  session_id: null,
  advice_status: "ready",
  advice: [
    "Tu as bien avancé sur les bases de données cette semaine.",
    "Garde ta série en révisant tes fiches ce soir.",
  ],
  block: blockRubric,
  reviews: { queue: 12, remaining: 3 },
  reminders: remindersRubric,
  offers: offersRubric,
  week: weekRubric,
  resource: resourceRubric,
  ...over,
});

/** A fake feed event (`ActivityItem`). */
export const activityItem = (id: string, at: string, over: Over = {}) => ({
  id,
  kind: "lesson",
  at,
  title: `Événement ${id}`,
  detail: null,
  link: null,
  ...over,
});

interface ActivityRow {
  id: string;
  at: string;
  [key: string]: unknown;
}

/** Greater than the `(at, id)` pair? Instants compare as dates; the `id` breaks ties. */
function after(row: ActivityRow, at: string, id: string | null): boolean {
  const gap = Date.parse(row.at) - Date.parse(at);
  if (gap !== 0) return gap > 0;
  return id !== null && row.id > id;
}

function before(row: ActivityRow, at: string, id: string | null): boolean {
  const gap = Date.parse(row.at) - Date.parse(at);
  if (gap !== 0) return gap < 0;
  return id !== null && row.id < id;
}

export interface HomeApiOptions {
  brief?: Over;
  events?: ActivityRow[];
  /** The first n brief reads fail (500). */
  briefFailures?: number;
  /** Feed reads fail for as long as this is true. */
  activityFails?: boolean;
}

/**
 * The brief and the activity feed in memory. The feed applies the `(at, id)` cursor as the server
 * does (exclusive bounds on the pair, most recent first, `limit`); `queries` keeps the
 * parameters received on each read, to check that the pair is sent.
 */
export function homeApi(options: HomeApiOptions = {}) {
  const state = {
    brief: briefOut(options.brief),
    events: [...(options.events ?? [])],
    briefReads: 0,
    briefFailures: options.briefFailures ?? 0,
    activityFails: options.activityFails ?? false,
    queries: [] as URLSearchParams[],
  };
  const handlers = [
    http.get(`${API}/brief/today`, () => {
      state.briefReads += 1;
      if (state.briefFailures > 0) {
        state.briefFailures -= 1;
        return HttpResponse.json(apiError("internal_error", "Le brief n'a pas pu être lu."), {
          status: 500,
        });
      }
      return HttpResponse.json(state.brief);
    }),
    http.get(`${API}/activity`, ({ request }) => {
      const params = new URL(request.url).searchParams;
      state.queries.push(params);
      if (state.activityFails) {
        return HttpResponse.json(apiError("internal_error", "Le fil n'a pas pu être lu."), {
          status: 500,
        });
      }
      const [newer, older] = [params.get("after"), params.get("before")];
      const rows = state.events
        .filter((row) => (newer ? after(row, newer, params.get("after_id")) : true))
        .filter((row) => (older ? before(row, older, params.get("before_id")) : true))
        .sort((a, b) => Date.parse(b.at) - Date.parse(a.at) || (a.id < b.id ? 1 : -1))
        .slice(0, Number(params.get("limit") ?? 20));
      return HttpResponse.json({ items: rows, latest_at: rows[0]?.at ?? null });
    }),
    http.get(`${API}/sessions/:id`, ({ params }) =>
      HttpResponse.json(sessionOut(String(params.id), "running", { graph: "daily_brief" })),
    ),
  ];
  return { handlers, state };
}
