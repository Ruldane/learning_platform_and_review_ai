import { api, apiBaseUrl } from "@/shared/api/client";
import { ApiError, unwrap } from "@/shared/api/errors";
import type { ClaimChoice } from "./types";

/**
 * The address to start Google sign-in (the backend answers with a redirect: plain link, never a
 * `fetch` call). `hint` pre-fills the email address at Google.
 */
export const loginUrl = (hint?: string): string => {
  const base = `${apiBaseUrl}/api/v1/auth/google/login`;
  return hint ? `${base}?login_hint=${encodeURIComponent(hint)}` : base;
};

/** `GET /auth/me`: the signed-in user (401 `auth_required` in Google mode without a session). */
export async function fetchMe(signal?: AbortSignal) {
  return unwrap(await api.GET("/auth/me", { signal }));
}

/**
 * The signed-in user, or `null`: a 401 `auth_required` is not a failure, it means
 * « pas de session » (any other error remains an error).
 */
export async function readMe(signal?: AbortSignal) {
  try {
    return await fetchMe(signal);
  } catch (error) {
    if (error instanceof ApiError && error.code === "auth_required") return null;
    throw error;
  }
}

/** `POST /auth/google/claim`: the first-sign-in choice; opens the session. */
export async function postClaim(choice: ClaimChoice) {
  return unwrap(await api.POST("/auth/google/claim", { body: { choice } }));
}

/** `POST /auth/logout`: 204, the cookie is cleared by the backend. */
export async function postLogout() {
  unwrap(await api.POST("/auth/logout"));
}
