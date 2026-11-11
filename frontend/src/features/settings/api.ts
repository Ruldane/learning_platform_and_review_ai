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

/** `GET /settings/models` : fournisseurs, modèles proposés et préréglages. */
export async function fetchModels(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/models", { signal }));
}
