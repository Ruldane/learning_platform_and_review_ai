import { api, apiBaseUrl } from "@/shared/api/client";
import { ApiError, unwrap } from "@/shared/api/errors";
import type { Me } from "./types";

/**
 * L'adresse de l'archive : un lien plein, jamais un appel `fetch` (le navigateur télécharge le
 * zip et prend son nom dans l'en-tête `Content-Disposition` du back, `tremplin-export-AAAAMMJJ.zip`).
 */
export const exportUrl = `${apiBaseUrl}/api/v1/account/export`;

/** `POST /account/delete` : 204 ; 422 `confirmation_required` si le mot n'est pas `SUPPRIMER`. */
export async function postDeleteAccount(confirm: string) {
  unwrap(await api.POST("/account/delete", { body: { confirm } }));
}

/**
 * `GET /auth/me`, lu pour le seul mode (`local` ou `google`). Un 401 `auth_required` vaut « pas de
 * session » (`null`), comme pour la porte de connexion qui partage cette clé de lecture.
 */
export async function fetchMe(signal?: AbortSignal): Promise<Me | null> {
  try {
    return unwrap(await api.GET("/auth/me", { signal }));
  } catch (error) {
    if (error instanceof ApiError && error.code === "auth_required") return null;
    throw error;
  }
}
