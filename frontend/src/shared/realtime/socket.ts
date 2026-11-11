import { apiBaseUrl } from "@/shared/api/client";
import type { SessionEvent } from "./types";

/** Ce que le flux attend d'un WebSocket : assez petit pour qu'un faux le remplace en test. */
export interface SocketLike {
  onopen: (() => void) | null;
  onmessage: ((e: { data: string }) => void) | null;
  onclose: ((e: { code: number }) => void) | null;
  close(): void;
}

export type SocketFactory = (url: string) => SocketLike;

/** Adapte le `WebSocket` du navigateur (seules les trames texte comptent : le serveur envoie du JSON). */
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

/** `http(s)://hôte` → `ws(s)://hôte/api/v1/sessions/{id}/stream?after_seq=N`. */
export function sessionStreamUrl(sessionId: string, afterSeq: number): string {
  const base = apiBaseUrl.replace(/^http/i, "ws").replace(/\/+$/, "");
  return `${base}/api/v1/sessions/${encodeURIComponent(sessionId)}/stream?after_seq=${afterSeq}`;
}

export const RECONNECT_DELAYS_MS = [500, 1000, 2000, 4000, 8000] as const;
/** Attente après la liste ci-dessus. */
export const RECONNECT_FALLBACK_MS = 10_000;
/** Fermetures anormales d'affilée (sans aucune donnée reçue entre elles) avant d'abandonner. */
export const MAX_RECONNECT_ATTEMPTS = 8;

/** Attente avant la reconnexion numéro `attempt` (1 pour la première). */
export function reconnectDelay(attempt: number): number {
  return RECONNECT_DELAYS_MS[attempt - 1] ?? RECONNECT_FALLBACK_MS;
}

/** Codes de fermeture reçus du serveur. */
export const CLOSE_FINISHED = 1000; // session terminée : fin définitive du flux
/**
 * Refus de politique. Inatteignable aujourd'hui depuis un navigateur : le serveur refuse l'origine,
 * un `after_seq` invalide ou un 401 AVANT `accept`, et le navigateur n'en voit qu'un 1006 anonyme
 * (D47, D49). Gardé pour un refus qui viendrait un jour après `accept`.
 */
export const CLOSE_POLICY = 1008;
/** Session inconnue ou d'un autre utilisateur : fermée APRÈS `accept`, code lisible (D47 §3). */
export const CLOSE_NOT_FOUND = 4404;

/** Lit une trame ; `null` si ce n'est pas un événement de session (trame ignorée). */
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
