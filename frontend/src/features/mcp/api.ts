import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { Decision, McpTokenCreateIn } from "./types";

/** Lignes lues dans le journal et la liste des changements (le contrat accepte jusqu'à 200). */
export const HISTORY_LIMIT = 50;

/** `GET /mcp/settings` : l'interrupteur général (coupé par défaut). */
export async function fetchSettings(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/settings", { signal }));
}

/** `PUT /mcp/settings` : allume ou coupe tout l'accès MCP d'un geste. */
export async function putEnabled(enabled: boolean) {
  return unwrap(await api.PUT("/mcp/settings", { body: { enabled } }));
}

/** `GET /mcp/features` : les features qui déclarent des outils, avec leurs outils par niveau. */
export async function fetchFeatures(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/features", { signal }));
}

/** `GET /mcp/actions` : la table des outils exposés et de leurs niveaux. */
export async function fetchActions(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/actions", { signal }));
}

/** `GET /mcp/tokens` : les jetons, jamais leur valeur. */
export async function fetchTokens(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/tokens", { signal }));
}

/** `POST /mcp/tokens` : la valeur du jeton n'est rendue qu'ici, une seule fois. */
export async function createToken(body: McpTokenCreateIn) {
  return unwrap(await api.POST("/mcp/tokens", { body }));
}

/** `DELETE /mcp/tokens/{id}` : révoque (le journal garde l'identifiant du jeton). */
export async function revokeToken(tokenId: string) {
  unwrap(await api.DELETE("/mcp/tokens/{token_id}", { params: { path: { token_id: tokenId } } }));
}

/** `GET /mcp/confirmations` : les demandes « À confirmer », en attente ou décidées. */
export async function fetchConfirmations(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/confirmations", { signal }));
}

/** `POST /mcp/confirmations/{id}/confirm|refuse` : exécute une seule fois, ou refuse. */
export async function decideConfirmation(confirmationId: string, decision: Decision) {
  const path = { confirmation_id: confirmationId };
  return unwrap(
    decision === "confirm"
      ? await api.POST("/mcp/confirmations/{confirmation_id}/confirm", { params: { path } })
      : await api.POST("/mcp/confirmations/{confirmation_id}/refuse", { params: { path } }),
  );
}

/** `GET /mcp/calls` : le journal des appels (outil, niveau, code, durée), jamais le contenu. */
export async function fetchCalls(signal?: AbortSignal) {
  return unwrap(
    await api.GET("/mcp/calls", { params: { query: { limit: HISTORY_LIMIT } }, signal }),
  );
}

/** `GET /mcp/changes` : les changements de niveau 2, de quoi les annuler. */
export async function fetchChanges(signal?: AbortSignal) {
  return unwrap(
    await api.GET("/mcp/changes", { params: { query: { limit: HISTORY_LIMIT } }, signal }),
  );
}

/** `POST /mcp/changes/{call_id}/undo` : remet les lignes dans leur état d'avant, si elles n'ont pas bougé. */
export async function undoChange(callId: string) {
  return unwrap(
    await api.POST("/mcp/changes/{call_id}/undo", { params: { path: { call_id: callId } } }),
  );
}
