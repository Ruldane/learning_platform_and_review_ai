import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { apiError } from "./councilHarness";
import { postingOut } from "./postingsApi";

type Over = Record<string, unknown>;

/** A debrief (`DebriefOut`): four scores, three strengths, three points to fix. */
export const debriefOut = (over: Over = {}) => ({
  scores: { clarity: 4, structure: 3, technical_depth: 2, role_fit: 5 },
  strengths: ["Exemples concrets", "Ton posé", "Résultats chiffrés"],
  fixes: ["Structure plus nette", "Plus de détails techniques", "Une conclusion"],
  weakest_index: 1,
  improved_answer: "Voici une réponse mieux construite.",
  missed: [1],
  expected: [{ index: 1, points: ["Citer le contexte", "Donner le résultat"] }],
  unrated: [],
  ...over,
});

/** An exchange (`ExchangeOut`). */
export const exchangeOut = (index: number, over: Over = {}) => ({
  index,
  question: `Question ${index + 1} du recruteur ?`,
  criterion: "clarity",
  source: "general",
  answer: `Ma réponse ${index + 1}.`,
  follow_up: null,
  follow_up_answer: null,
  note: 4,
  unrated: false,
  ...over,
});

/** An interview (`InterviewOut`) finished by default. */
export const interviewOut = (over: Over = {}) => ({
  id: "iv1",
  application_id: "a1",
  posting_id: null,
  role: null,
  mode: "mixed",
  duration_min: 15,
  language: "fr",
  session_id: "iv-s1",
  status: "done",
  exchanges: [exchangeOut(0), exchangeOut(1, { note: 2 }), exchangeOut(2)],
  debrief: debriefOut(),
  flags: [],
  cards_created: 1,
  created_at: "2026-11-12T10:00:00Z",
  ...over,
});

export interface InterviewApiOptions {
  /** Interviews already there (most recent first). */
  interviews?: Over[];
  /** The offers from `GET /postings`. */
  postings?: Over[];
  /** Overrides the launch (`POST …/interviews`): `body` is the body received. */
  start?: (body: Over) => Response | undefined;
  /** Overrides reading the list (a failure, for example). */
  list?: () => Response | undefined;
}

const newState = () => ({
  starts: [] as { applicationId: string | null; body: Over }[],
  lists: [] as (string | null)[],
  postingReads: 0,
});

/** What an accepted launch stores: an interview in progress, at the top of the list. */
function accept(interviews: Over[], applicationId: string | null, body: Over) {
  const interview = interviewOut({
    id: "iv-new",
    application_id: applicationId,
    posting_id: body.posting_id ?? null,
    role: body.role ?? null,
    mode: body.mode,
    duration_min: body.duration_min,
    language: body.language ?? "fr",
    session_id: "iv-s-new",
    status: "running",
    exchanges: [],
    debrief: null,
    cards_created: 0,
    created_at: "2026-11-15T09:00:00Z",
  });
  interviews.unshift(interview);
  return HttpResponse.json(
    { interview_id: interview.id, session_id: interview.session_id },
    { status: 202 },
  );
}

/**
 * The interview routes, in memory: a launch stores a `running` interview, `finish`
 * ends it, as the real server does. `state` keeps the bodies received.
 */
export function interviewApi(options: InterviewApiOptions = {}) {
  const interviews: Over[] = [...(options.interviews ?? [])];
  const state = newState();
  const start =
    (applicationId: string | null) =>
    async ({ request }: { request: Request }) => {
      const body = (await request.json()) as Over;
      state.starts.push({ applicationId, body });
      return options.start?.(body) ?? accept(interviews, applicationId, body);
    };
  return {
    state,
    interviews,
    handlers: [
      http.get(`${API}/interviews`, ({ request }) => {
        const applicationId = new URL(request.url).searchParams.get("application_id");
        state.lists.push(applicationId);
        const custom = options.list?.();
        if (custom) return custom;
        const rows = applicationId
          ? interviews.filter((row) => row.application_id === applicationId)
          : interviews;
        return HttpResponse.json(rows);
      }),
      http.get(`${API}/interviews/:id`, ({ params }) => {
        const found = interviews.find((row) => row.id === params.id);
        return found
          ? HttpResponse.json(found)
          : HttpResponse.json(apiError("interview_not_found", "Entretien introuvable."), {
              status: 404,
            });
      }),
      http.post(`${API}/applications/:id/interviews`, ({ params, request }) =>
        start(String(params.id))({ request }),
      ),
      http.post(`${API}/interviews`, start(null)),
      http.get(`${API}/postings`, () => {
        state.postingReads += 1;
        return HttpResponse.json(options.postings ?? [postingOut({ id: "p1" })]);
      }),
    ],
    /** The server finishes interview `id` (what the session does when it stores its result). */
    finish(id: string, over: Over = {}) {
      const row = interviews.find((candidate) => candidate.id === id);
      if (!row) return;
      const done = interviewOut({ exchanges: [exchangeOut(0), exchangeOut(1, { note: 2 })] });
      Object.assign(row, { status: "done", exchanges: done.exchanges, debrief: done.debrief });
      Object.assign(row, { cards_created: 1 }, over);
    },
  };
}
