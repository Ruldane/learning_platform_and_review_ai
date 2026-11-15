import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { apiError } from "./councilHarness";
import { versionOut } from "./cvFixtures";

type Over = Record<string, unknown>;

const PERSONAS = ["ats_reader", "recruiter", "manager", "colleague"] as const;

/** Les quatre votes d'un comité (`VoteOut`) : trois oui, un non, par défaut. */
export const votesOut = (votes: string[] = ["oui", "oui", "non", "oui"]) =>
  PERSONAS.map((persona, index) => ({
    persona,
    vote: votes[index] ?? "oui",
    objection: `Objection de ${persona}.`,
    reason: `Raison de ${persona}.`,
  }));

/** Un changement (`ChangeOut`). */
export const changeOut = (over: Over = {}) => ({
  text: "Chiffre le résultat de ton projet principal.",
  persona: "manager",
  fact_ids: [],
  needs_skill: false,
  terms: [],
  ...over,
});

/** Une exécution du comité (`CommitteeRunOut`) terminée par défaut : verdict « oui », trois changements. */
export const committeeOut = (over: Over = {}) => ({
  id: "c1",
  cv_version_id: "v1",
  posting_id: "p1",
  application_id: "a1",
  session_id: "cm-s1",
  status: "done",
  votes: votesOut(),
  verdict: "oui",
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

/** Une exécution qui délibère encore : rien à lire que le fil. */
export const runningCommittee = (over: Over = {}) =>
  committeeOut({
    status: "running",
    verdict: null,
    votes: [],
    objections: [],
    changes: [],
    ...over,
  });

/** L'avant et l'après (`CommitteeDiff`). */
export const diffOut = (over: Over = {}) => ({
  previous_id: "c0",
  votes: PERSONAS.map((persona, index) => ({
    persona,
    before: index === 0 ? "non" : "oui",
    after: "oui",
  })),
  objections_resolved: ["Mot clé Kubernetes absent."],
  objections_new: ["Résumé trop long."],
  ...over,
});

export interface CommitteeApiOptions {
  /** Les exécutions déjà là (la plus récente d'abord). */
  runs?: Over[];
  /** Les versions de CV de l'offre (`VersionOut`) ; une version prête par défaut. */
  versions?: Over[];
  /** Remplace le lancement (`POST /committee`) : `body` est le corps reçu. */
  start?: (body: Over) => Response | undefined;
  /** Remplace la lecture d'une exécution (une panne, par exemple). */
  read?: (id: string) => Response | undefined;
}

const newState = () => ({
  starts: [] as Over[],
  lists: [] as string[],
  reads: [] as string[],
  versionReads: [] as string[],
});

/** Ce qu'un lancement accepté range : une exécution qui délibère, la précédente terminée devient son « avant ». */
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

/** Ce que `finish` range : le résultat, avec l'avant / après si une exécution terminée précède. */
function finishRun(runs: Over[], id: string, over: Over) {
  const row = runs.find((candidate) => candidate.id === id);
  if (!row) return;
  const before = runs.find((candidate) => candidate !== row && candidate.status === "done");
  const done = committeeOut({ previous: before ? diffOut({ previous_id: before.id }) : null });
  const { votes, verdict, objections, changes, previous } = done;
  Object.assign(row, { status: "done", verdict, votes, objections, changes, previous }, over);
}

/**
 * Les routes du comité, en mémoire : un lancement range une exécution `running`, `finish` la termine
 * (avec son avant / après si une exécution terminée la précède), comme le vrai serveur. `state` garde
 * les corps et les lectures reçus.
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
    /** Le serveur termine l'exécution `id` (ce que fait la session en rangeant son résultat). */
    finish: (id: string, over: Over = {}) => finishRun(runs, id, over),
  };
}
