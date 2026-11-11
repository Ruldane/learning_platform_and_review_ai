import createClient, { type Middleware } from "openapi-fetch";
import { errorFromResponse, networkError } from "./errors";
import type { paths } from "./schema";

export const apiBaseUrl: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const API_PREFIX = "/api/v1";

/** Chemins du contrat sans le préfixe `/api/v1` (porté par la `baseUrl` du client). */
type WithoutPrefix<P> = {
  [K in keyof P as K extends `${typeof API_PREFIX}${infer Rest}` ? Rest : K]: P[K];
};

/** Toute réponse en échec devient une `ApiError` ; une panne réseau aussi. */
const errorMiddleware: Middleware = {
  async onResponse({ response }) {
    if (!response.ok) throw await errorFromResponse(response);
    return undefined;
  },
  onError({ error }) {
    // Une annulation volontaire (AbortController, signal de TanStack Query) n'est pas une panne.
    if (error instanceof Error && error.name === "AbortError") return undefined;
    return networkError();
  },
};

export const api = createClient<WithoutPrefix<paths>>({
  baseUrl: `${apiBaseUrl}${API_PREFIX}`,
  // Résolu à chaque appel (et non à la création) : MSW peut remplacer `fetch` après coup.
  fetch: (request) => globalThis.fetch(request),
});

api.use(errorMiddleware);
