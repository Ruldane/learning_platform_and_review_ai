import createClient, { type Middleware } from "openapi-fetch";
import { getRunSource, RUN_HEADER } from "@/shared/lib/runSource";
import { emitAuthRequired } from "./authEvents";
import { errorFromResponse, networkError } from "./errors";
import type { paths } from "./schema";

export const apiBaseUrl: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const API_PREFIX = "/api/v1";

/** Chemins du contrat sans le préfixe `/api/v1` (porté par la `baseUrl` du client). */
type WithoutPrefix<P> = {
  [K in keyof P as K extends `${typeof API_PREFIX}${infer Rest}` ? Rest : K]: P[K];
};

/**
 * Toute réponse en échec devient une `ApiError` ; une panne réseau aussi. Un 401 `auth_required`
 * prévient en plus la porte de connexion (`authEvents`), qui mène à `/login`.
 */
const errorMiddleware: Middleware = {
  async onResponse({ response }) {
    if (!response.ok) {
      const error = await errorFromResponse(response);
      if (response.status === 401 && error.code === "auth_required") emitAuthRequired();
      throw error;
    }
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
  // Le cookie de session (`tremplin_session`) part avec chaque appel, même vers un autre port.
  credentials: "include",
  // Résolu à chaque appel (et non à la création) : MSW peut remplacer `fetch` après coup.
  fetch: (request) => globalThis.fetch(request),
});

/** Le choix du menu « Qui fait tourner les agents » part avec chaque appel (lu par le back au
 * lancement d'un parcours seulement). */
const runSourceMiddleware: Middleware = {
  onRequest({ request }) {
    const source = getRunSource();
    if (source !== "settings" && !request.headers.has(RUN_HEADER)) {
      request.headers.set(RUN_HEADER, source);
    }
    return request;
  },
};

api.use(errorMiddleware);
api.use(runSourceMiddleware);
