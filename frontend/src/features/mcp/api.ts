import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { Decision, McpTokenCreateIn } from "./types";

/** Lines read from the log and the change list (the contract accepts up to 200). */
export const HISTORY_LIMIT = 50;

/** `GET /mcp/settings`: the master switch (off by default). */
export async function fetchSettings(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/settings", { signal }));
}

/** `PUT /mcp/settings`: turns all MCP access on or off in one action. */
export async function putEnabled(enabled: boolean) {
  return unwrap(await api.PUT("/mcp/settings", { body: { enabled } }));
}

/** `GET /mcp/features`: the features that declare tools, with their tools per level. */
export async function fetchFeatures(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/features", { signal }));
}

/** `GET /mcp/actions`: the table of exposed tools and their levels. */
export async function fetchActions(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/actions", { signal }));
}

/** `GET /mcp/tokens`: the tokens, never their value. */
export async function fetchTokens(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/tokens", { signal }));
}

/** `POST /mcp/tokens`: the token value is returned here only, once. */
export async function createToken(body: McpTokenCreateIn) {
  return unwrap(await api.POST("/mcp/tokens", { body }));
}

/** `DELETE /mcp/tokens/{id}`: revokes (the log keeps the token id). */
export async function revokeToken(tokenId: string) {
  unwrap(await api.DELETE("/mcp/tokens/{token_id}", { params: { path: { token_id: tokenId } } }));
}

/** `GET /mcp/confirmations`: the « À confirmer » requests, pending or decided. */
export async function fetchConfirmations(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/confirmations", { signal }));
}

/** `POST /mcp/confirmations/{id}/confirm|refuse`: runs once, or refuses. */
export async function decideConfirmation(confirmationId: string, decision: Decision) {
  const path = { confirmation_id: confirmationId };
  return unwrap(
    decision === "confirm"
      ? await api.POST("/mcp/confirmations/{confirmation_id}/confirm", { params: { path } })
      : await api.POST("/mcp/confirmations/{confirmation_id}/refuse", { params: { path } }),
  );
}

/** `GET /mcp/calls`: the call log (tool, level, code, duration), never the content. */
export async function fetchCalls(signal?: AbortSignal) {
  return unwrap(
    await api.GET("/mcp/calls", { params: { query: { limit: HISTORY_LIMIT } }, signal }),
  );
}

/** `GET /mcp/changes`: the level 2 changes, so they can be undone. */
export async function fetchChanges(signal?: AbortSignal) {
  return unwrap(
    await api.GET("/mcp/changes", { params: { query: { limit: HISTORY_LIMIT } }, signal }),
  );
}

/** `POST /mcp/changes/{call_id}/undo`: restores the earlier row state if rows have not moved. */
export async function undoChange(callId: string) {
  return unwrap(
    await api.POST("/mcp/changes/{call_id}/undo", { params: { path: { call_id: callId } } }),
  );
}
