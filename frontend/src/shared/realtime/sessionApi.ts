import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import type { UserCommand } from "./types";

/** Appels REST des sessions (14.1) : toute action passe par ici, jamais par le WebSocket. */
export type SessionView = components["schemas"]["SessionView"];

const path = (sessionId: string) => ({ params: { path: { session_id: sessionId } } });

export async function startSession(graph: string, input: Record<string, unknown>): Promise<string> {
  const created = unwrap(await api.POST("/sessions", { body: { graph, input } }));
  return created.session_id;
}

export async function fetchSession(sessionId: string, signal?: AbortSignal): Promise<SessionView> {
  return unwrap(await api.GET("/sessions/{session_id}", { ...path(sessionId), signal }));
}

export async function postResume(
  sessionId: string,
  interruptId: string | null,
  value: unknown,
): Promise<SessionView> {
  return unwrap(
    await api.POST("/sessions/{session_id}/resume", {
      ...path(sessionId),
      body: { interrupt_id: interruptId, value },
    }),
  );
}

export async function postMessage(sessionId: string, text: string): Promise<void> {
  unwrap(await api.POST("/sessions/{session_id}/message", { ...path(sessionId), body: { text } }));
}

/** Commande du débat (« Plus court », « Passer aux propositions »…) : un message sans texte (D82). */
export async function postCommand(
  sessionId: string,
  command: NonNullable<UserCommand>,
): Promise<void> {
  unwrap(
    await api.POST("/sessions/{session_id}/message", {
      ...path(sessionId),
      body: { text: "", command },
    }),
  );
}

export async function postPause(sessionId: string): Promise<SessionView> {
  return unwrap(await api.POST("/sessions/{session_id}/pause", path(sessionId)));
}

export async function postCancel(sessionId: string): Promise<SessionView> {
  return unwrap(await api.POST("/sessions/{session_id}/cancel", path(sessionId)));
}
