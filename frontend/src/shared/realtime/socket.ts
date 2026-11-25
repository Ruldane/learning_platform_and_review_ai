import { apiBaseUrl } from "@/shared/api/client";
import type { SessionEvent } from "./types";

/** What the stream expects from a WebSocket: small enough that a fake can replace it in tests. */
export interface SocketLike {
  onopen: (() => void) | null;
  onmessage: ((e: { data: string }) => void) | null;
  onclose: ((e: { code: number }) => void) | null;
  close(): void;
}

export type SocketFactory = (url: string) => SocketLike;

/** Adapts the browser's `WebSocket` (only text frames count: the server sends JSON). */
export const browserSocket: SocketFactory = (url) => {
  const ws = new WebSocket(url);
  const socket: SocketLike = {
    onopen: null,
    onmessage: null,
    onclose: null,
    close: () => ws.close(),
  };
  ws.onopen = () => socket.onopen?.();
  ws.onmessage = (e: MessageEvent) => {
    if (typeof e.data === "string") socket.onmessage?.({ data: e.data });
  };
  ws.onclose = (e: CloseEvent) => socket.onclose?.({ code: e.code });
  return socket;
};

/** `http(s)://host` → `ws(s)://host/api/v1/sessions/{id}/stream?after_seq=N`. */
export function sessionStreamUrl(sessionId: string, afterSeq: number): string {
  const base = apiBaseUrl.replace(/^http/i, "ws").replace(/\/+$/, "");
  return `${base}/api/v1/sessions/${encodeURIComponent(sessionId)}/stream?after_seq=${afterSeq}`;
}

export const RECONNECT_DELAYS_MS = [500, 1000, 2000, 4000, 8000] as const;
/** Delay once the list above is exhausted. */
export const RECONNECT_FALLBACK_MS = 10_000;
/** Consecutive abnormal closes (no data received between them) before giving up. */
export const MAX_RECONNECT_ATTEMPTS = 8;

/** Wait before reconnection number `attempt` (1 for the first). */
export function reconnectDelay(attempt: number): number {
  return RECONNECT_DELAYS_MS[attempt - 1] ?? RECONNECT_FALLBACK_MS;
}

/** Close codes received from the server. */
export const CLOSE_FINISHED = 1000; // session ended: final end of the stream
/**
 * Policy refusal. Unreachable from a browser today: the server refuses the origin,
 * an invalid `after_seq` or a 401 BEFORE `accept`, and the browser only sees an anonymous 1006
 * (D47, D49). Kept for a refusal that might one day come after `accept`.
 */
export const CLOSE_POLICY = 1008;
/** Unknown session, or another user's: closed AFTER `accept`, readable code (D47 §3). */
export const CLOSE_NOT_FOUND = 4404;

/** Reads a frame; `null` if it is not a session event (frame ignored). */
export function parseEventFrame(data: string): SessionEvent | null {
  let value: unknown;
  try {
    value = JSON.parse(data);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null) return null;
  const { seq, type } = value as Record<string, unknown>;
  if (typeof seq !== "number" || !Number.isInteger(seq) || typeof type !== "string") return null;
  return value as SessionEvent;
}
