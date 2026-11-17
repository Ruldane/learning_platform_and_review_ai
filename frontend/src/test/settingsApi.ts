import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** Un agent de `GET /settings/agents`. */
export const agentOut = (name: string, tier: string) => ({ name, tier });

/** La 422 du back pour des champs refusés : leurs chemins seulement, jamais une valeur. */
export const refusedFieldsResponse = (...fields: string[]) =>
  HttpResponse.json(
    {
      error: {
        code: "validation_error",
        message: "Requête invalide : vérifie les champs signalés.",
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
      state.settings = { ...state.settings, ...body, vision_enabled: true };
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
