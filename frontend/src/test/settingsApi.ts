import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** Une porte fermée : `promise` pour `settingsApi({ gate })`, `open()` pour la rouvrir. */
export function closedGate() {
  let open = () => {};
  const promise = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { promise, open };
}

/** Un agent de `GET /settings/agents`. */
export const agentOut = (name: string, tier: string) => ({ name, tier });

/** La 422 du back pour des champs refusés : leurs chemins seulement, jamais une valeur. */
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
  /** Les réglages lus (`SettingsOut`) : le premier état du faux serveur. */
  settings: Record<string, unknown>;
  models?: object;
  keys?: object[];
  agents?: object[];
  /** Réponse à un `PUT /settings` : une réponse brute (ex. une 422), ou rien pour l'accepter. */
  put?: (body: Record<string, unknown>) => Response | undefined;
  /** Tient chaque `PUT /settings` jusqu'à l'ouverture de la porte : pour agir pendant l'envoi. */
  gate?: Promise<void>;
}

/**
 * Ce que rend le vrai back : le budget hebdomadaire est recalculé (5 jours de semaine + le plus
 * long bloc de week-end).
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
 * Faux serveur des réglages : `GET`/`PUT /settings` en mémoire (une écriture se lit ensuite),
 * modèles, clés et agents. Garde les corps reçus et le nombre de lectures des agents.
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
