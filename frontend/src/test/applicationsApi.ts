import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";
import { apiError } from "./councilHarness";

type Over = Record<string, unknown>;

/** Une fiche de la liste (`ApplicationOut`) fictive. */
export const applicationOut = (over: Over = {}) => ({
  id: "a1",
  company: "Acme",
  title: "Data engineer",
  status: "applied",
  channel: "linkedin",
  applied_on: "2026-11-03",
  interview_on: null,
  next_action: "Relancer",
  next_action_on: "2026-11-20",
  due_reminders: 1,
  posting_id: null,
  cv_version_id: null,
  cv_version_number: null,
  url: "https://example.org/jobs/1",
  created_at: "2026-11-03T08:00:00Z",
  updated_at: "2026-11-03T08:00:00Z",
  ...over,
});

/** Une relance complète (`ReminderOut`). */
export const reminderOut = (over: Over = {}) => ({
  id: "r1",
  application_id: "a1",
  kind: "linkedin_7",
  due_on: "2026-11-10",
  status: "pending",
  company: "Acme",
  title: "Data engineer",
  contact: { id: "c1", name: "Camille Durand", role: "Responsable data", url: null },
  linkedin_search_url: null,
  channel: "linkedin",
  draft: "Bonjour Camille, je me permets de revenir vers vous.",
  ...over,
});

export const statsOut = (over: Over = {}) => ({
  by_status: { to_apply: 1, applied: 2, interview: 1 },
  response_rate: 0.4,
  mean_response_days: 6.5,
  due_reminders: 1,
  ...over,
});

/** Une alerte de doublon (`AlertOut`). */
export const alertOut = (over: Over = {}) => ({
  application_id: "a9",
  level: "probable",
  message: "Attention, tu as déjà une fiche chez Acme pour le poste Data engineer.",
  company: "Acme",
  title: "Data engineer",
  status: "applied",
  applied_on: "2026-11-03",
  created_on: "2026-11-03",
  ...over,
});

export const eventOut = (over: Over = {}) => ({
  id: "e1",
  kind: "created",
  at: "2026-11-03T08:00:00Z",
  status_from: null,
  status_to: null,
  text: null,
  ref_id: null,
  ...over,
});

/** La fiche ouverte (`ApplicationDetail`) : une fiche de la liste et ce que le détail y ajoute. */
export const detailOut = (row: Over = applicationOut(), extra: Over = {}) => ({
  ...row,
  posting_text: row.posting_text ?? null,
  letter: null,
  notes: "Premier échange par téléphone.",
  contacts: [{ id: "c1", name: "Camille Durand", role: "Responsable data", url: null }],
  events: [eventOut()],
  reminders: [],
  ...extra,
});

export interface ApplicationsApiOptions {
  /** Les fiches de la liste. */
  applications?: Over[];
  /** Ce que le détail d'une fiche ajoute à sa ligne, par identifiant. */
  details?: Record<string, Over>;
  /** Les relances (toutes, `pending` par défaut). */
  reminders?: Over[];
  stats?: Over;
  /** Remplace la lecture de la liste (une panne, par exemple). */
  list?: () => Response;
  /** Remplace la création (`POST /applications`) : `body` est le corps reçu. */
  create?: (body: Over) => Response;
  /** Remplace l'écriture d'un événement. */
  event?: (id: string, body: Over) => Response;
  /** Remplace la lecture des relances dues (une panne, par exemple). */
  reminderList?: () => Response;
  /** Remplace l'action sur une relance. */
  reminderAction?: (id: string, action: string) => Response;
  /** Remplace le démarrage de la saisie en une phrase. */
  intake?: (body: Over) => Response;
  /** Réponse de `GET /applications/check` (sans `own` ni alerte par défaut). */
  check?: (query: URLSearchParams) => Response;
}

const newState = () => ({
  events: [] as { id: string; body: Over }[],
  patches: [] as { id: string; body: Over }[],
  creates: [] as Over[],
  reminderActions: [] as { id: string; action: string }[],
  intakes: [] as Over[],
  checks: [] as string[],
  cancels: [] as string[],
});

export type ApplicationsState = ReturnType<typeof newState>;

/** Ce que les routes partagent : les options, les corps reçus et les données en mémoire. */
interface Context {
  options: ApplicationsApiOptions;
  state: ApplicationsState;
  rows: Over[];
  reminders: Over[];
  details: Record<string, Over>;
}

let tick = 0;
/** Une écriture change `updated_at`, comme le serveur : la page qui en dépend le voit. */
const touch = (row: Over) => {
  tick += 1;
  row.updated_at = `2026-11-15T10:00:${String(tick % 60).padStart(2, "0")}.${String(tick).padStart(3, "0")}Z`;
};

const missing = () =>
  HttpResponse.json(apiError("application_not_found", "Cette fiche n'existe pas."), {
    status: 404,
  });

function detailOf(ctx: Context, id: string) {
  const row = ctx.rows.find((item) => item.id === id);
  if (!row) return null;
  const own = ctx.reminders.filter((item) => item.application_id === id);
  return detailOut(row, { reminders: own, ...ctx.details[id] });
}

const pendingOf = (ctx: Context) => ctx.reminders.filter((item) => item.status === "pending");

function readRoutes(ctx: Context) {
  const { options, state } = ctx;
  return [
    http.get(`${API}/applications`, () => options.list?.() ?? HttpResponse.json(ctx.rows)),
    http.get(`${API}/applications/stats`, () =>
      HttpResponse.json(statsOut({ due_reminders: pendingOf(ctx).length, ...options.stats })),
    ),
    http.get(`${API}/applications/check`, ({ request }) => {
      const query = new URL(request.url).searchParams;
      state.checks.push(query.toString());
      return options.check?.(query) ?? HttpResponse.json({ own: null, alerts: [], info: [] });
    }),
    http.get(`${API}/applications/:id`, ({ params }) => {
      const detail = detailOf(ctx, String(params.id));
      return detail ? HttpResponse.json(detail) : missing();
    }),
  ];
}

function eventRoute(ctx: Context) {
  return http.post(`${API}/applications/:id/events`, async ({ request, params }) => {
    const id = String(params.id);
    const body = (await request.json()) as Over;
    ctx.state.events.push({ id, body });
    const custom = ctx.options.event?.(id, body);
    if (custom) return custom;
    const row = ctx.rows.find((item) => item.id === id);
    if (!row) return missing();
    if (body.kind === "status") row.status = body.status;
    if (body.kind === "status" && body.status === "applied")
      row.applied_on = body.on ?? "2026-11-15";
    if (body.interview_on) row.interview_on = body.interview_on;
    touch(row);
    return HttpResponse.json(detailOf(ctx, id));
  });
}

function patchRoute(ctx: Context) {
  return http.patch(`${API}/applications/:id`, async ({ request, params }) => {
    const id = String(params.id);
    const body = (await request.json()) as Over;
    ctx.state.patches.push({ id, body });
    const row = ctx.rows.find((item) => item.id === id);
    if (!row) return missing();
    const { contacts, ...fields } = body;
    Object.assign(row, fields);
    touch(row);
    if (contacts) ctx.details[id] = { ...ctx.details[id], contacts };
    return HttpResponse.json(detailOf(ctx, id));
  });
}

function createRoutes(ctx: Context) {
  return [
    http.post(`${API}/applications/intake`, async ({ request }) => {
      const body = (await request.json()) as Over;
      ctx.state.intakes.push(body);
      return ctx.options.intake?.(body) ?? HttpResponse.json({ session_id: "i1" }, { status: 202 });
    }),
    http.post(`${API}/applications`, async ({ request }) => {
      const body = (await request.json()) as Over;
      ctx.state.creates.push(body);
      const custom = ctx.options.create?.(body);
      if (custom) return custom;
      const row = applicationOut({
        id: "new1",
        company: body.company ?? "Acme",
        title: body.title ?? "Data engineer",
        status: body.status ?? "to_apply",
        due_reminders: 0,
      });
      ctx.rows.push(row);
      return HttpResponse.json({ application: detailOut(row), info: [] }, { status: 201 });
    }),
  ];
}

function reminderRoutes(ctx: Context) {
  return [
    http.get(
      `${API}/reminders`,
      () => ctx.options.reminderList?.() ?? HttpResponse.json(pendingOf(ctx)),
    ),
    http.patch(`${API}/reminders/:id`, async ({ request, params }) => {
      const id = String(params.id);
      const { action } = (await request.json()) as { action: string };
      ctx.state.reminderActions.push({ id, action });
      const custom = ctx.options.reminderAction?.(id, action);
      if (custom) return custom;
      const reminder = ctx.reminders.find((item) => item.id === id);
      if (!reminder) {
        return HttpResponse.json(apiError("reminder_not_found", "Introuvable."), { status: 404 });
      }
      if (action !== "postpone") reminder.status = action === "done" ? "done" : "ignored";
      return HttpResponse.json(reminder);
    }),
  ];
}

function sessionRoutes(ctx: Context) {
  return [
    http.get(`${API}/sessions/:id`, ({ params }) =>
      HttpResponse.json(
        sessionOut(String(params.id), "running", {
          graph: "application_intake",
          subject_type: "application_intake",
        }),
      ),
    ),
    http.post(`${API}/sessions/:id/cancel`, ({ params }) => {
      ctx.state.cancels.push(String(params.id));
      return HttpResponse.json(
        sessionOut(String(params.id), "cancelled", { graph: "application_intake" }),
      );
    }),
  ];
}

/**
 * Les routes des candidatures et des relances, en mémoire : une écriture (déplacement, retouche,
 * relance traitée) change ce que les lectures suivantes rendent, comme le vrai serveur. `state`
 * garde les corps reçus.
 */
export function applicationsApi(options: ApplicationsApiOptions = {}) {
  const state = newState();
  const rows: Over[] = options.applications ?? [applicationOut()];
  const reminders: Over[] = options.reminders ?? [];
  const ctx: Context = { options, state, rows, reminders, details: { ...options.details } };
  const handlers = [
    ...readRoutes(ctx),
    eventRoute(ctx),
    patchRoute(ctx),
    ...createRoutes(ctx),
    ...reminderRoutes(ctx),
    ...sessionRoutes(ctx),
  ];
  return { state, handlers, rows, reminders };
}
