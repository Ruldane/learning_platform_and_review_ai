import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { apiError } from "./councilHarness";
import { versionOut } from "./cvFixtures";

type Over = Record<string, unknown>;

const PERSONAS = ["ats_reader", "recruiter", "manager", "colleague"] as const;

/** A committee's four votes (`VoteOut`): three yes, one no, by default. */
export const votesOut = (votes: string[] = ["yes", "yes", "no", "yes"]) =>
  PERSONAS.map((persona, index) => ({
    persona,
    vote: votes[index] ?? "yes",
    objection: `Objection de ${persona}.`,
    reason: `Raison de ${persona}.`,
  }));

/** A change (`ChangeOut`). */
export const changeOut = (over: Over = {}) => ({
  text: "Chiffre le résultat de ton projet principal.",
  persona: "manager",
  fact_ids: [],
  needs_skill: false,
  terms: [],
  ...over,
});

/** A committee run (`CommitteeRunOut`) finished by default: verdict "yes", three changes. */
export const committeeOut = (over: Over = {}) => ({
  id: "c1",
  cv_version_id: "v1",
  posting_id: "p1",
  application_id: "a1",
  session_id: "cm-s1",
  status: "done",
  votes: votesOut(),
  verdict: "yes",
  objections: [
    { text: "Peu de résultats chiffrés.", personas: ["manager", "recruiter"] },
    { text: "Mot clé Kubernetes absent.", personas: ["ats_reader"] },
  ],
  changes: [
    changeOut(),
    changeOut({
      text: "À acquérir : Kubernetes. Ton profil ne le dit pas : ne l'écris pas dans ton CV.",
      persona: "ats_reader",
      needs_skill: true,
      terms: ["Kubernetes"],
    }),
    changeOut({ text: "Resserre le résumé.", persona: "recruiter" }),
  ],
  previous: null,
  created_at: "2026-11-14T10:00:00Z",
  ...over,
});

/** A run still deliberating: nothing to read but the feed. */
export const runningCommittee = (over: Over = {}) =>
  committeeOut({
    status: "running",
    verdict: null,
    votes: [],
    objections: [],
    changes: [],
    ...over,
  });

/** Before and after (`CommitteeDiff`). */
export const diffOut = (over: Over = {}) => ({
  previous_id: "c0",
  votes: PERSONAS.map((persona, index) => ({
    persona,
    before: index === 0 ? "no" : "yes",
    after: "yes",
  })),
  objections_resolved: ["Mot clé Kubernetes absent."],
  objections_new: ["Résumé trop long."],
  ...over,
});

export interface CommitteeApiOptions {
  /** Runs already there (most recent first). */
  runs?: Over[];
  /** The offer's CV versions (`VersionOut`); one ready version by default. */
  versions?: Over[];
  /** Overrides the launch (`POST /committee`): `body` is the body received. */
  start?: (body: Over) => Response | undefined;
  /** Overrides reading a run (a failure, for example). */
  read?: (id: string) => Response | undefined;
}

const newState = () => ({
  starts: [] as Over[],
  lists: [] as string[],
  reads: [] as string[],
  versionReads: [] as string[],
});

/** What an accepted launch stores: a deliberating run; the last finished one is its "before". */
function accept(runs: Over[], body: Over) {
  const run = runningCommittee({
    id: `c${runs.length + 1}-new`,
    cv_version_id: body.cv_version_id,
    session_id: "cm-s-new",
    created_at: "2026-11-15T09:00:00Z",
  });
  runs.unshift(run);
  return HttpResponse.json({ run_id: run.id, session_id: run.session_id }, { status: 202 });
}

type State = ReturnType<typeof newState>;

function readRoutes(runs: Over[], versions: Over[], state: State, options: CommitteeApiOptions) {
  return [
    http.get(`${API}/committee`, ({ request }) => {
      state.lists.push(new URL(request.url).searchParams.get("posting_id") ?? "");
      return HttpResponse.json(runs);
    }),
    http.get(`${API}/committee/:id`, ({ params }) => {
      const id = String(params.id);
      state.reads.push(id);
      const custom = options.read?.(id);
      if (custom) return custom;
      const found = runs.find((row) => row.id === id);
      return found
        ? HttpResponse.json(found)
        : HttpResponse.json(apiError("committee_not_found", "Exécution introuvable."), {
            status: 404,
          });
    }),
    http.get(`${API}/cv/versions`, ({ request }) => {
      state.versionReads.push(new URL(request.url).searchParams.get("posting_id") ?? "");
      return HttpResponse.json(versions);
    }),
  ];
}

/** What `finish` stores: the result, with before / after if a finished run precedes it. */
function finishRun(runs: Over[], id: string, over: Over) {
  const row = runs.find((candidate) => candidate.id === id);
  if (!row) return;
  const before = runs.find((candidate) => candidate !== row && candidate.status === "done");
  const done = committeeOut({ previous: before ? diffOut({ previous_id: before.id }) : null });
  const { votes, verdict, objections, changes, previous } = done;
  Object.assign(row, { status: "done", verdict, votes, objections, changes, previous }, over);
}

/**
 * The committee routes, in memory: a launch stores a `running` run, `finish` ends it
 * (with its before / after if a finished run precedes it), as the real server does. `state` keeps
 * the bodies and reads received.
 */
export function committeeApi(options: CommitteeApiOptions = {}) {
  const runs: Over[] = [...(options.runs ?? [])];
  const versions: Over[] = options.versions ?? [versionOut({ id: "v1", number: 1 })];
  const state = newState();
  const start = http.post(`${API}/committee`, async ({ request }) => {
    const body = (await request.json()) as Over;
    state.starts.push(body);
    return options.start?.(body) ?? accept(runs, body);
  });
  return {
    state,
    runs,
    versions,
    handlers: [...readRoutes(runs, versions, state, options), start],
    /** The server finishes run `id` (what the session does when it stores its result). */
    finish: (id: string, over: Over = {}) => finishRun(runs, id, over),
  };
}
