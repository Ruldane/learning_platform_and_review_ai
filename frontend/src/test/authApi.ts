import { http, HttpResponse } from "msw";
import { apiBaseUrl } from "@/shared/api/client";

const AUTH = `${apiBaseUrl}/api/v1/auth`;

/** Identité fictive des tests (jamais une vraie adresse). */
export const camille = {
  id: "u-camille",
  email: "camille.exemple@example.org",
  name: "Camille Exemple",
  auth_mode: "google",
};

export const localMe = { id: "local", email: null, name: null, auth_mode: "local" };

export const authRequired = {
  error: { code: "auth_required", message: "Connexion requise.", details: null },
};

/** Enveloppe d'erreur du back pour un test (`{error: {code, message, details}}`). */
export function errorBody(code: string, message = "Erreur.", details: unknown = null) {
  return { error: { code, message, details } };
}

export interface AuthApi {
  handlers: ReturnType<typeof http.get>[];
  /** Nombre d'appels reçus par `GET /auth/me`. */
  readonly meCalls: number;
  /** Nombre d'appels reçus par `POST /auth/logout`. */
  readonly logoutCalls: number;
  /** Corps reçu par `POST /auth/google/claim`. */
  readonly claimBodies: unknown[];
}

interface AuthApiOptions {
  /** Réponse de `GET /auth/me` : une identité (200) ou `null` (401 `auth_required`). */
  me?: typeof camille | typeof localMe | null;
  /** `GET /auth/me` répond 500. */
  meFails?: boolean;
  /** Réponse de `POST /auth/google/claim` : l'identité (200) ou une erreur 409. */
  claim?: typeof camille | { conflict: string };
}

/** Faux serveur d'authentification : `me`, `logout`, `claim`, avec des compteurs d'appels. */
export function authApi(options: AuthApiOptions = {}): AuthApi {
  const state = { meCalls: 0, logoutCalls: 0, claimBodies: [] as unknown[] };
  let signedIn = options.me ?? null;
  const handlers = [
    http.get(`${AUTH}/me`, () => {
      state.meCalls += 1;
      if (options.meFails) return HttpResponse.json(errorBody("boom"), { status: 500 });
      return signedIn
        ? HttpResponse.json(signedIn)
        : HttpResponse.json(authRequired, { status: 401 });
    }),
    http.post(`${AUTH}/logout`, () => {
      state.logoutCalls += 1;
      signedIn = null;
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(`${AUTH}/google/claim`, async ({ request }) => {
      state.claimBodies.push(await request.json());
      const claim = options.claim ?? camille;
      if ("conflict" in claim) {
        return HttpResponse.json(errorBody(claim.conflict, "Reprise impossible."), { status: 409 });
      }
      signedIn = claim;
      return HttpResponse.json(claim);
    }),
  ];
  return {
    handlers: handlers as AuthApi["handlers"],
    get meCalls() {
      return state.meCalls;
    },
    get logoutCalls() {
      return state.logoutCalls;
    },
    get claimBodies() {
      return state.claimBodies;
    },
  };
}
