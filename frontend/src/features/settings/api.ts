import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { UserSettings } from "./types";

/** `GET /settings`. */
export async function fetchSettings(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings", { signal }));
}

/** `PUT /settings`: full replacement (the body is a `UserSettings`). */
export async function putSettings(body: UserSettings) {
  return unwrap(await api.PUT("/settings", { body }));
}

/** `GET /settings/api-keys`: one entry per provider, never the key in clear text. */
export async function fetchApiKeys(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/api-keys", { signal }));
}

/** `POST /settings/api-keys`: the key is sent only in this body, never in the URL. */
export async function postApiKey(provider: string, key: string) {
  return unwrap(await api.POST("/settings/api-keys", { body: { provider, key } }));
}

/** `DELETE /settings/api-keys/{provider}`: removes only the key entered in the interface. */
export async function deleteApiKey(provider: string) {
  unwrap(await api.DELETE("/settings/api-keys/{provider}", { params: { path: { provider } } }));
}

/** `POST /settings/api-keys/{provider}/test`: minimal call to the provider. */
export async function testApiKey(provider: string) {
  return unwrap(
    await api.POST("/settings/api-keys/{provider}/test", { params: { path: { provider } } }),
  );
}

/** `GET /settings/agents`: the agents whose model is overridden, in registry order. */
export async function fetchAgents(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/agents", { signal }));
}

/** `GET /settings/models`: providers, suggested models and presets. */
export async function fetchModels(signal?: AbortSignal) {
  return unwrap(await api.GET("/settings/models", { signal }));
}

/** `GET /research/usage`: Brave usage for the UTC calendar month, and whether a key is set. */
export async function fetchSearchUsage(signal?: AbortSignal) {
  return unwrap(await api.GET("/research/usage", { signal }));
}

/** `GET /health`: the state of each service, always 200 (`status` says whether all is well). */
export async function fetchHealth(signal?: AbortSignal) {
  return unwrap(await api.GET("/health", { signal }));
}

/** `GET /health/embedding`: progress of the embeddings model (public, like `/health`). */
export async function fetchEmbeddingProgress(signal?: AbortSignal) {
  return unwrap(await api.GET("/health/embedding", { signal }));
}

export interface ProfileImport {
  cv: File;
  linkedin?: File;
}

/**
 * `POST /profile/import` (202): the CV as PDF and, optionally, the LinkedIn profile as PDF, in
 * multipart (the browser sets the boundary). 409 `capture_in_progress`, 413 `file_too_large`,
 * 415 `unsupported_file_type`.
 */
export async function importProfile({ cv, linkedin }: ProfileImport, source?: RunSource) {
  const form = new FormData();
  form.append("cv", cv);
  if (linkedin) form.append("linkedin", linkedin);
  // The contract types a file as a string: the real body is the form.
  return unwrap(
    await api.POST("/profile/import", {
      body: { cv: "" },
      bodySerializer: () => form,
      headers: runSourceHeaders(source),
    }),
  );
}
