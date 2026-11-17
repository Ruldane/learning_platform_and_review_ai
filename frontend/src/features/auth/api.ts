import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { ClaimChoice } from "./types";

/**
 * L'adresse du départ vers Google (le back répond par une redirection : lien plein, jamais un
 * appel `fetch`). `hint` préremplit l'adresse e-mail chez Google.
 */
export const loginUrl = (hint?: string): string => {
  const base = `${apiBaseUrl}/api/v1/auth/google/login`;
  return hint ? `${base}?login_hint=${encodeURIComponent(hint)}` : base;
};

/** `GET /auth/me` : l'utilisateur connecté (401 `auth_required` en mode Google sans session). */
export async function fetchMe(signal?: AbortSignal) {
  return unwrap(await api.GET("/auth/me", { signal }));
}

/** `POST /auth/google/claim` : le choix de la première connexion ; ouvre la session. */
export async function postClaim(choice: ClaimChoice) {
  return unwrap(await api.POST("/auth/google/claim", { body: { choice } }));
}

/** `POST /auth/logout` : 204, le cookie est effacé par le back. */
export async function postLogout() {
  unwrap(await api.POST("/auth/logout"));
}
