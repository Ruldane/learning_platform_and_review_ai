import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { UserSettings } from "./types";

/** `GET /settings`. */
export async function fetchSettings(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings", { signal }));
}

/** `PUT /settings` : remplacement complet (le corps est un `UserSettings`). */
export async function putSettings(body: UserSettings) {
  return unwrap(await api.PUT("/settings", { body }));
}

/** `GET /settings/api-keys` : une entrée par fournisseur, jamais la clé en clair. */
export async function fetchApiKeys(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/api-keys", { signal }));
}

/** `POST /settings/api-keys` : la clé n'est envoyée que dans ce corps, jamais dans l'URL. */
export async function postApiKey(provider: string, key: string) {
  return unwrap(await api.POST("/settings/api-keys", { body: { provider, key } }));
}

/** `DELETE /settings/api-keys/{provider}` : ne supprime que la clé saisie dans l'interface. */
export async function deleteApiKey(provider: string) {
  unwrap(await api.DELETE("/settings/api-keys/{provider}", { params: { path: { provider } } }));
}

/** `POST /settings/api-keys/{provider}/test` : appel minimal chez le fournisseur. */
export async function testApiKey(provider: string) {
  return unwrap(
    await api.POST("/settings/api-keys/{provider}/test", { params: { path: { provider } } }),
  );
}

/** `GET /settings/agents` : les agents dont le modèle se surcharge, dans l'ordre du registre. */
export async function fetchAgents(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/agents", { signal }));
}

/** `GET /settings/models` : fournisseurs, modèles proposés et préréglages. */
export async function fetchModels(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/models", { signal }));
}

/** `GET /research/usage` : consommation Brave du mois civil UTC et présence d'une clé. */
export async function fetchSearchUsage(signal?: AbortSignal) {
  return unwrap(await api.GET("/research/usage", { signal }));
}

/** `GET /health` : l'état de chaque service, toujours 200 (`status` dit si tout va bien). */
export async function fetchHealth(signal?: AbortSignal) {
  return unwrap(await api.GET("/health", { signal }));
}

/** `GET /health/embedding` : la progression du modèle d'embeddings (public, comme `/health`). */
export async function fetchEmbeddingProgress(signal?: AbortSignal) {
  return unwrap(await api.GET("/health/embedding", { signal }));
}

export interface ProfileImport {
  cv: File;
  linkedin?: File;
}

/**
 * `POST /profile/import` (202) : le CV en PDF et, au choix, le profil LinkedIn en PDF, en
 * multipart (le navigateur pose la frontière). 409 `capture_in_progress`, 413 `file_too_large`,
 * 415 `unsupported_file_type`.
 */
export async function importProfile({ cv, linkedin }: ProfileImport) {
  const form = new FormData();
  form.append("cv", cv);
  if (linkedin) form.append("linkedin", linkedin);
  // Le contrat type un fichier comme une chaîne : le corps réel est le formulaire.
  return unwrap(
    await api.POST("/profile/import", { body: { cv: "" }, bodySerializer: () => form }),
  );
}
