import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** A closed gate: `promise` for `settingsApi({ gate })`, `open()` to reopen it. */
export function closedGate() {
  let open = () => {};
  const promise = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { promise, open };
}

/** An agent from `GET /settings/agents`. */
export const agentOut = (name: string, tier: string) => ({ name, tier });

/** The back's 422 for refused fields: their paths only, never a value. */
export const refusedFieldsResponse = (...fields: string[]) =>
  HttpResponse.json(
    {
      error: {
        code: "validation_error",
        message: "Invalid request. Check the highlighted fields.",
        details: { fields },
      },
    },
    { status: 422 },
  );

interface SettingsApiOptions {
  /** The settings read (`SettingsOut`): the fake server's first state. */
  settings: Record<string, unknown>;
  models?: object;
  keys?: object[];
  agents?: object[];
  /** Response to a `PUT /settings`: a raw response (e.g. a 422), or nothing to accept it. */
  put?: (body: Record<string, unknown>) => Response | undefined;
  /** Holds each `PUT /settings` until the gate opens: to act during the send. */
  gate?: Promise<void>;
}

/**
 * What the real back returns: the weekly budget is recomputed (5 weekdays + the
 * longest weekend block).
 */
function withBudget(settings: Record<string, unknown>) {
  const availability = settings.availability as Record<string, number> | undefined;
  if (!availability) return settings;
  const { weekday_minutes: day, weekend_block_max_minutes: weekend } = availability;
  return {
    ...settings,
    availability: { ...availability, weekly_budget_minutes: 5 * day! + weekend! },
  };
}

/**
 * Fake settings server: `GET`/`PUT /settings` in memory (a write reads back afterwards),
 * models, keys and agents. Keeps the bodies received and the number of agent reads.
 */
export function settingsApi(options: SettingsApiOptions) {
  const state = { settings: options.settings };
  const puts: Record<string, unknown>[] = [];
  const counts = { agents: 0 };
  const handlers = [
    http.get(`${API}/settings`, () => HttpResponse.json(state.settings)),
    http.put(`${API}/settings`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      puts.push(body);
      const refusal = options.put?.(body);
      if (refusal) return refusal;
      await options.gate;
      state.settings = withBudget({ ...state.settings, ...body, vision_enabled: true });
      return HttpResponse.json(state.settings);
    }),
    http.get(`${API}/settings/api-keys`, () => HttpResponse.json(options.keys ?? [])),
    http.get(`${API}/settings/models`, () =>
      HttpResponse.json(options.models ?? { providers: [], presets: {} }),
    ),
    http.get(`${API}/settings/agents`, () => {
      counts.agents += 1;
      return HttpResponse.json(options.agents ?? []);
    }),
  ];
  return { handlers, state, puts, counts };
}
