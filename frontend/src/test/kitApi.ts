import { http, HttpResponse } from "msw";
import { API } from "./councilApi";
import { apiError } from "./councilHarness";

type Over = Record<string, unknown>;

/** The seven pieces, in the server's fixed order. */
export const KIT_KINDS = [
  "cv",
  "letter",
  "linkedin",
  "followups",
  "form_answers",
  "company_brief",
  "pitch",
] as const;

/** A piece not yet stored (`KitItemOut`, status `pending`). */
export const pendingItem = (kind: string): Over => ({
  id: null,
  kind,
  status: "pending",
  content: "",
  flags: [],
  salary_fields: 0,
  words: null,
  error: null,
  sources: [],
  edited: false,
  updated_at: null,
});

/** A stored piece, `ready` by default. */
export const kitItem = (kind: string, over: Over = {}): Over => ({
  ...pendingItem(kind),
  id: `k-${kind}`,
  status: "ready",
  content: `Texte de la pièce ${kind}.`,
  words: 5,
  updated_at: "2026-11-15T10:00:00Z",
  ...over,
});

export interface KitApiOptions {
  /** Pieces already stored; the others are `pending`. */
  items?: Over[];
  running?: boolean;
  sessionId?: string | null;
  /** Overrides reading the kit (a failure, for example): `undefined` keeps the normal response. */
  read?: () => Response | undefined;
  /** Overrides starting the kit (`POST /applications/{id}/kit`). */
  start?: () => Response;
  /** Overrides editing a piece. */
  patch?: (kind: string, body: Over) => Response;
}

let tick = 0;

/** What the server does with edited text: piece edited, re-read (ready if nothing is missing). */
function applyPatch(item: Over, content: string) {
  tick += 1;
  item.content = content;
  item.edited = true;
  item.updated_at = `2026-11-15T11:00:${String(tick % 60).padStart(2, "0")}Z`;
  if (content.trim() === "") item.status = "to_check";
  else if (item.status === "to_check" || item.status === "failed") {
    item.status = "ready";
    item.flags = [];
    item.error = null;
  }
}

const newState = (options: KitApiOptions) => ({
  running: options.running ?? false,
  sessionId: options.sessionId ?? null,
  starts: 0,
  reads: 0,
  patches: [] as { kind: string; body: Over }[],
});

interface Context {
  options: KitApiOptions;
  state: ReturnType<typeof newState>;
  items: Over[];
}

function readRoutes({ options, state, items }: Context) {
  return [
    http.get(`${API}/applications/:id/kit`, () => {
      state.reads += 1;
      const custom = options.read?.();
      if (custom) return custom;
      return HttpResponse.json({ session_id: state.sessionId, running: state.running, items });
    }),
  ];
}

function writeRoutes({ options, state, items }: Context) {
  return [
    http.post(`${API}/applications/:id/kit`, () => {
      state.starts += 1;
      const custom = options.start?.();
      if (custom) return custom;
      state.running = true;
      state.sessionId = "k1";
      return HttpResponse.json({ session_id: "k1" }, { status: 202 });
    }),
    http.patch(`${API}/applications/:id/kit/:kind`, async ({ request, params }) => {
      const kind = String(params.kind);
      const body = (await request.json()) as Over;
      state.patches.push({ kind, body });
      const custom = options.patch?.(kind, body);
      if (custom) return custom;
      const item = items.find((candidate) => candidate.kind === kind);
      if (!item || item.status === "pending") {
        return HttpResponse.json(apiError("kit_item_not_found", "Pièce introuvable."), {
          status: 404,
        });
      }
      applyPatch(item, String(body.content));
      return HttpResponse.json(item);
    }),
  ];
}

/**
 * The kit routes, in memory: a piece arriving (`arrive`) or an edit changes what
 * `GET /applications/{id}/kit` returns next, as the real server does. `state` keeps the calls.
 */
export function kitApi(options: KitApiOptions = {}) {
  const items: Over[] = KIT_KINDS.map(
    (kind) => options.items?.find((item) => item.kind === kind) ?? pendingItem(kind),
  );
  const ctx: Context = { options, state: newState(options), items };
  return {
    state: ctx.state,
    items,
    handlers: [...readRoutes(ctx), ...writeRoutes(ctx)],
    /** The server stores a piece (what the session does before emitting `artifact.ready`). */
    arrive(kind: string, over: Over = {}) {
      items[items.findIndex((item) => item.kind === kind)] = kitItem(kind, over);
    },
    /** The session is finished. */
    finish() {
      ctx.state.running = false;
    },
  };
}
