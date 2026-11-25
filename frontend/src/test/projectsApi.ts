import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";
import { apiError } from "./councilHarness";
import { summaryOf, submissionOut } from "./projectsFixtures";

export * from "./projectsFixtures";

type Over = Record<string, unknown>;

export interface ProjectsApiOptions {
  /** Projects (`projectOut`), in program order. */
  projects?: Over[];
  /** The master-profile version that adding an entry creates (default 4). */
  nextVersion?: number;
  /** The terms a « à vérifier » draft keeps when edited (default: none, it becomes ready). */
  recheckFlags?: string[];
  /** Overrides the response of `POST /projects/{id}/submit`. */
  submitReply?: () => Response;
  /** Overrides the response of `PATCH /projects/{id}/drafts/{kind}`. */
  draftReply?: () => Response;
  /** Overrides the response of `POST /projects/{id}/profile-entry`. */
  entryReply?: () => Response;
  /** Overrides the response of `POST /projects/{id}/brief`. */
  briefReply?: () => Response;
  /** Overrides the response of `POST /projects/{id}/drafts`. */
  draftsReply?: () => Response;
  /** The session that `POST /projects/{id}/drafts` returns (default `sess-drafts-<id>`). */
  draftsSessionId?: string;
  /** Overrides the response of `GET /projects`. */
  listReply?: () => Response;
}

/** A received render: the multipart body cannot be re-read under jsdom (see `api.test.ts`). */
export interface SubmitRecord {
  id: string;
  contentType: string;
}

interface ProjectsState {
  projects: Over[];
  options: ProjectsApiOptions;
  submits: SubmitRecord[];
  patches: { id: string; kind: string; body: Over }[];
  entries: { id: string; body: Over }[];
  briefs: string[];
  /** The draft regeneration requests (`POST /projects/{id}/drafts`). */
  regenerations: string[];
  listReads: number;
  /** The reads of `GET /projects/{id}`. */
  reads: number;
  sessions: number;
}

const notFound = () =>
  HttpResponse.json(apiError("project_not_found", "Projet introuvable."), { status: 404 });

const conflict = (code: string, message: string, details: unknown = null) =>
  HttpResponse.json(apiError(code, message, details), { status: 409 });

const find = (state: ProjectsState, id: unknown) => state.projects.find((row) => row.id === id);

const update = (state: ProjectsState, id: string, over: Over) => {
  state.projects = state.projects.map((row) => (row.id === id ? { ...row, ...over } : row));
  return find(state, id)!;
};

/** What the server refuses before accepting a render (409), or `null`. */
function submitRefusal(project: Over): Response | null {
  if (project.status === "validated") {
    return conflict(
      "project_validated",
      "Ce projet est déjà validé : il ne se rend pas une seconde fois.",
    );
  }
  if (project.status === "reviewing") {
    return conflict(
      "review_in_progress",
      "Ton rendu est en cours d'évaluation : attends son résultat.",
      {
        session_id: project.session_id,
      },
    );
  }
  if (!project.brief) {
    return conflict("project_not_ready", "L'énoncé de ce projet n'est pas encore écrit.");
  }
  return null;
}

function readHandlers(state: ProjectsState) {
  return [
    http.get(`${API}/projects`, ({ request }) => {
      state.listReads += 1;
      if (state.options.listReply) return state.options.listReply();
      const status = new URL(request.url).searchParams.get("status");
      return HttpResponse.json(
        state.projects.filter((p) => !status || p.status === status).map(summaryOf),
      );
    }),
    // A session's tracking reads its state before opening the stream.
    http.get(`${API}/sessions/:id`, ({ params }) =>
      HttpResponse.json(sessionOut(String(params.id), "running", { graph: "project_review" })),
    ),
    http.get(`${API}/projects/:id`, ({ params }) => {
      state.reads += 1;
      const project = find(state, params.id);
      return project ? HttpResponse.json(project) : notFound();
    }),
    http.get(`${API}/projects/:id/github-claims`, () => HttpResponse.json([])),
    http.get(
      `${API}/projects/:id/screenshots/:n`,
      () =>
        new HttpResponse(new Uint8Array([137, 80, 78, 71]), {
          headers: { "Content-Type": "image/png" },
        }),
    ),
  ];
}

function submitHandler(state: ProjectsState) {
  return http.post(`${API}/projects/:id/submit`, ({ request, params }) => {
    const contentType = request.headers.get("content-type") ?? "";
    state.submits.push({ id: String(params.id), contentType });
    if (state.options.submitReply) return state.options.submitReply();
    const project = find(state, params.id);
    if (!project) return notFound();
    const refused = submitRefusal(project);
    if (refused) return refused;
    state.sessions += 1;
    const session = `sess-${String(params.id)}-${state.sessions}`;
    update(state, String(params.id), {
      status: "reviewing",
      session_id: session,
      submissions: [
        submissionOut({
          at: `2026-11-16T1${state.sessions}:00:00Z`,
          repo_url: null,
          description: "Un rendu envoyé par la page.",
          screenshots: 0,
        }),
        ...(project.submissions as Over[]),
      ],
    });
    return HttpResponse.json({ session_id: session }, { status: 202 });
  });
}

function draftHandler(state: ProjectsState) {
  return http.patch(`${API}/projects/:id/drafts/:kind`, async ({ request, params }) => {
    if (state.options.draftReply) return state.options.draftReply();
    const body = (await request.json()) as Over;
    const kind = String(params.kind);
    state.patches.push({ id: String(params.id), kind, body });
    const project = find(state, params.id);
    if (!project) return notFound();
    const drafts = (project.drafts as Over[]).map((draft) => {
      if (draft.kind !== kind) return draft;
      const flags: string[] =
        draft.status === "to_check"
          ? (state.options.recheckFlags ?? [])
          : (draft.flags as string[]);
      const status = draft.status === "to_check" && flags.length === 0 ? "ready" : draft.status;
      return { ...draft, content: body.content, edited: true, flags, status };
    });
    return HttpResponse.json(update(state, String(params.id), { drafts }));
  });
}

function entryHandler(state: ProjectsState) {
  return http.post(`${API}/projects/:id/profile-entry`, async ({ request, params }) => {
    state.entries.push({ id: String(params.id), body: (await request.json()) as Over });
    if (state.options.entryReply) return state.options.entryReply();
    const project = find(state, params.id);
    if (!project) return notFound();
    if (project.status !== "validated") {
      return conflict(
        "project_not_validated",
        "Seul un projet validé peut entrer dans ton profil.",
      );
    }
    if (project.profile_version !== null) {
      return conflict("entry_already_added", "Ce projet est déjà dans ton profil maître.");
    }
    return HttpResponse.json(
      update(state, String(params.id), { profile_version: state.options.nextVersion ?? 4 }),
    );
  });
}

function briefHandler(state: ProjectsState) {
  return http.post(`${API}/projects/:id/brief`, ({ params }) => {
    state.briefs.push(String(params.id));
    if (state.options.briefReply) return state.options.briefReply();
    const project = find(state, params.id);
    if (!project) return notFound();
    if (project.status !== "brief_failed") {
      return conflict("brief_not_failed", "L'énoncé de ce projet n'est pas en échec.");
    }
    update(state, String(params.id), {
      status: "brief_pending",
      session_id: `sess-brief-${String(params.id)}`,
    });
    return HttpResponse.json({ session_id: `sess-brief-${String(params.id)}` }, { status: 202 });
  });
}

function regenerateHandler(state: ProjectsState) {
  return http.post(`${API}/projects/:id/drafts`, ({ params }) => {
    state.regenerations.push(String(params.id));
    if (state.options.draftsReply) return state.options.draftsReply();
    const project = find(state, params.id);
    if (!project) return notFound();
    if (project.status !== "validated") {
      return conflict("project_not_validated", "Seul un projet validé a des brouillons.");
    }
    if ((project.drafts as Over[]).length > 0) {
      return conflict("drafts_present", "Ce projet a déjà ses brouillons.");
    }
    const session = state.options.draftsSessionId ?? `sess-drafts-${String(params.id)}`;
    return HttpResponse.json({ session_id: session }, { status: 202 });
  });
}

/**
 * In-memory projects: `projects` is the test's to edit (`settle` changes a project, as the
 * server does when its session ends); `submits`, `patches`, `entries` and `briefs` keep what
 * the page sent.
 */
export function projectsApi(options: ProjectsApiOptions = {}) {
  const state: ProjectsState = {
    projects: [...(options.projects ?? [])],
    options,
    submits: [],
    patches: [],
    entries: [],
    briefs: [],
    regenerations: [],
    listReads: 0,
    reads: 0,
    sessions: 0,
  };
  const settle = (id: string, over: Over) => update(state, id, over);
  const handlers = [
    ...readHandlers(state),
    submitHandler(state),
    draftHandler(state),
    entryHandler(state),
    briefHandler(state),
    regenerateHandler(state),
  ];
  return { handlers, state, settle };
}
