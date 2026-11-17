/// <reference types="node" />
import { createHash } from "node:crypto";
import { http, HttpResponse, type HttpHandler } from "msw";
import { errorBody } from "./authApi";
import { API } from "./councilApi";

type Over = Record<string, unknown>;

/** Les empreintes sha256 des fichiers, comme le serveur les donne (`file_hashes`). */
export const hashesOf = (files: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(files).map(([name, text]) => [
      name,
      createHash("sha256").update(text).digest("hex"),
    ]),
  );

export const exerciseOut = (over: Over = {}) => ({
  id: "e1",
  title: "Additionner",
  statement: "Écris une fonction add(a, b).",
  files: { "main.py": "def add(a, b):\n    return a - b\n" },
  entry: "main.py",
  origin: "user",
  topic: null,
  created_at: "2026-11-17T09:00:00Z",
  ...over,
});

export const sessionSummary = (over: Over = {}) => ({
  id: "s1",
  title: "Additionner",
  exercise_id: "e1",
  updated_at: "2026-11-17T10:00:00Z",
  passed: false,
  passed_at: null,
  ...over,
});

export const sessionOut = (over: Over = {}) => {
  const session = {
    ...sessionSummary(),
    files: { "main.py": "print('bonjour')\n" } as Record<string, string>,
    entry: "main.py",
    ...over,
  };
  return { ...session, file_hashes: hashesOf(session.files) };
};

/** Une exécution de la liste de la séance : par défaut lancée par Claude (MCP), déjà finie. */
export const runOut = (over: Over = {}) => ({
  id: "rc1",
  session_id: "s1",
  kind: "run",
  entry: "main.py",
  status: "done",
  created_at: "2026-11-17T10:20:00Z",
  origin: "mcp",
  ...over,
});

export const noteOut = (over: Over = {}) => ({
  id: "n1",
  session_id: "s1",
  kind: "hint",
  author: "professor",
  author_label: null,
  origin: "app",
  status: "open",
  file_path: null,
  line_start: null,
  line_end: null,
  content: "Relis la ligne du retour.",
  replacement: null,
  base_hash: null,
  reference_note_id: null,
  level: null,
  created_at: "2026-11-17T10:05:00Z",
  ...over,
});

export const usageOut = (over: Over = {}) => ({
  session_tokens: 12_340,
  day_tokens: 45_000,
  session_cap: 100_000,
  day_cap: 300_000,
  mode_on_demand: false,
  ...over,
});

export const preferencesOut = (over: Over = {}) => ({
  teacher_mode: "auto",
  idle_trigger: false,
  teacher_style: "guide",
  mcp_can_write_files: false,
  session_cap: 100_000,
  day_cap: 300_000,
  ...over,
});

export const progress = (over: Over = {}) => ({
  id: "r1",
  status: "done",
  output: "",
  next_offset: 0,
  exit_code: 0,
  duration_ms: 120,
  truncated: false,
  ...over,
});

interface IdeApi {
  exercises?: unknown[];
  sessions?: unknown[];
  session?: Over;
  notes?: unknown[];
  /** Les exécutions de la séance (`GET /ide/sessions/{id}/runs`) ; modifiable en cours de test. */
  runs?: unknown[];
  usage?: Over;
  preferences?: Over;
  /** Les lectures successives de `GET /ide/runs/{id}` ; la dernière se répète. */
  reads?: unknown[];
  /** La réponse de `POST /teach` (202). */
  teach?: Over;
  /** Réponse de `POST /notes/{id}/accept` : la séance après application, ou 409 périmée. */
  accept?: "ok" | "stale";
  acceptedFiles?: Record<string, string>;
  /** Réponse de `POST /runs` : « busy » = 409. */
  run?: "ok" | "busy";
  /** Des handlers qui passent avant les autres (une panne précise). */
  override?: HttpHandler[];
}

type Calls = ReturnType<typeof newCalls>;

const newCalls = () => ({
  teach: [] as unknown[],
  reads: [] as number[],
  runs: [] as unknown[],
  puts: [] as unknown[],
  prefs: [] as unknown[],
  accepts: [] as string[],
  rejects: [] as string[],
  exercises: [] as unknown[],
  generated: [] as unknown[],
  sessions: [] as unknown[],
  usage: 0,
  sessionReads: 0,
  noteReads: 0,
  runListReads: 0,
});

/** Les lectures et les écritures des exercices, des séances, des réglages et de la consommation. */
function dataHandlers(api: IdeApi, calls: Calls): HttpHandler[] {
  return [
    http.get(`${API}/ide/exercises`, () => HttpResponse.json(api.exercises ?? [exerciseOut()])),
    http.post(`${API}/ide/exercises`, async ({ request }) => {
      const body = (await request.json()) as Over;
      calls.exercises.push(body);
      return HttpResponse.json(exerciseOut(body), { status: 201 });
    }),
    http.post(`${API}/ide/exercises/generate`, async ({ request }) => {
      calls.generated.push(await request.json());
      return HttpResponse.json({ session_id: "g1" }, { status: 202 });
    }),
    http.get(`${API}/ide/sessions`, () => HttpResponse.json(api.sessions ?? [])),
    http.post(`${API}/ide/sessions`, async ({ request }) => {
      calls.sessions.push(await request.json());
      return HttpResponse.json(sessionOut({ id: "s-new", ...api.session }), { status: 201 });
    }),
    http.get(`${API}/ide/sessions/:id`, () => {
      calls.sessionReads += 1;
      return HttpResponse.json(sessionOut(api.session));
    }),
    http.put(`${API}/ide/sessions/:id/files`, async ({ request }) => {
      const body = (await request.json()) as {
        files: Record<string, string>;
        base_hashes?: Record<string, string>;
      };
      calls.puts.push(body);
      const clash = staleFiles(sessionOut(api.session).files, body);
      if (clash.length > 0) {
        const stale = errorBody("stale_base", "Claude a modifié des fichiers.", { files: clash });
        return HttpResponse.json(stale, { status: 409 });
      }
      api.session = { ...api.session, files: body.files }; // le serveur garde ce qu'on lui envoie
      return HttpResponse.json(sessionOut(api.session));
    }),
    http.get(`${API}/ide/preferences`, () => HttpResponse.json(preferencesOut(api.preferences))),
    http.put(`${API}/ide/preferences`, async ({ request }) => {
      const body = (await request.json()) as Over;
      calls.prefs.push(body);
      return HttpResponse.json(body);
    }),
    http.get(`${API}/ide/usage`, () => {
      calls.usage += 1;
      return HttpResponse.json(usageOut(api.usage));
    }),
  ];
}

/** Les fichiers que l'envoi écraserait alors que le serveur n'a plus la version éditée (409). */
function staleFiles(
  current: Record<string, string>,
  body: { files: Record<string, string>; base_hashes?: Record<string, string> },
): string[] {
  const now = hashesOf(current);
  return Object.entries(body.base_hashes ?? {})
    .filter(([name, hash]) => now[name] !== hash && body.files[name] !== current[name])
    .map(([name]) => name);
}

/** Les exécutions et la lecture de leur sortie. */
function runHandlers(api: IdeApi, calls: Calls): HttpHandler[] {
  const reads = [...(api.reads ?? [progress()])] as Over[];
  return [
    http.post(`${API}/ide/sessions/:id/runs`, async ({ request }) => {
      calls.runs.push(await request.json());
      if (api.run === "busy") {
        return HttpResponse.json(errorBody("run_busy", "Une exécution est déjà en cours."), {
          status: 409,
        });
      }
      const run = { id: "r1", session_id: "s1", kind: "run", entry: "main.py", origin: "app" };
      const created_at = "2026-11-17T10:10:00Z";
      return HttpResponse.json({ ...run, status: "running", created_at }, { status: 202 });
    }),
    http.get(`${API}/ide/sessions/:id/runs`, () => {
      calls.runListReads += 1;
      return HttpResponse.json(api.runs ?? []);
    }),
    http.get(`${API}/ide/runs/:id`, ({ request }) => {
      calls.reads.push(Number(new URL(request.url).searchParams.get("after")));
      return HttpResponse.json((reads.length > 1 ? reads.shift() : reads[0]) as Over);
    }),
  ];
}

/** Le professeur : son réveil, ses notes, les décisions sur les propositions. */
function teacherHandlers(api: IdeApi, calls: Calls): HttpHandler[] {
  return [
    http.post(`${API}/ide/sessions/:id/teach`, async ({ request }) => {
      calls.teach.push(await request.json());
      return HttpResponse.json(api.teach ?? { session_id: "t1" }, { status: 202 });
    }),
    http.get(`${API}/ide/sessions/:id/notes`, () => {
      calls.noteReads += 1;
      return HttpResponse.json(api.notes ?? []);
    }),
    http.post(`${API}/ide/notes/:id/accept`, ({ params }) => {
      calls.accepts.push(String(params.id));
      if (api.accept === "stale") {
        const stale = errorBody("note_stale", "Le code a changé depuis.");
        return HttpResponse.json(stale, { status: 409 });
      }
      const files = api.acceptedFiles ?? { "main.py": "print('corrigé')\n" };
      api.session = { ...api.session, files };
      return HttpResponse.json(sessionOut(api.session));
    }),
    http.post(`${API}/ide/notes/:id/reject`, ({ params }) => {
      calls.rejects.push(String(params.id));
      return HttpResponse.json(noteOut({ id: String(params.id), status: "rejected" }));
    }),
  ];
}

/** Faux serveur de l'IDE (les 17 routes utilisées) ; garde les corps et les appels reçus. */
export function ideApi(api: IdeApi = {}) {
  const calls = newCalls();
  const handlers = [
    ...(api.override ?? []),
    ...dataHandlers(api, calls),
    ...runHandlers(api, calls),
    ...teacherHandlers(api, calls),
  ];
  return { handlers, calls };
}
