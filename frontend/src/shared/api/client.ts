import createClient, { type Middleware } from "openapi-fetch";
import { getRunSource, RUN_HEADER } from "@/shared/lib/runSource";
import { emitAuthRequired } from "./authEvents";
import { errorFromResponse, networkError } from "./errors";
import type { paths } from "./schema";

export const apiBaseUrl: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const API_PREFIX = "/api/v1";

/** Contract paths without the `/api/v1` prefix (carried by the client's `baseUrl`). */
type WithoutPrefix<P> = {
  [K in keyof P as K extends `${typeof API_PREFIX}${infer Rest}` ? Rest : K]: P[K];
};

/**
 * Any failed response becomes an `ApiError`; so does a network failure. A 401 `auth_required`
 * also notifies the sign-in gate (`authEvents`), which leads to `/login`.
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
    // A deliberate cancellation (AbortController, TanStack Query signal) is not a failure.
    if (error instanceof Error && error.name === "AbortError") return undefined;
    return networkError();
  },
};

export const api = createClient<WithoutPrefix<paths>>({
  baseUrl: `${apiBaseUrl}${API_PREFIX}`,
  // The session cookie (`tremplin_session`) goes with every call, even to another port.
  credentials: "include",
  // Resolved on each call (not at creation): MSW may replace `fetch` afterwards.
  fetch: (request) => globalThis.fetch(request),
});

/** The « Qui fait tourner les agents » menu choice goes with every call (read by the back only at
 * launch of a run). */
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
