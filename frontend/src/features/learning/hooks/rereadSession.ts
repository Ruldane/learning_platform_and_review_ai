import { fetchSession } from "@/shared/realtime/sessionApi";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { snapshotOf } from "@/shared/realtime/statusGate";
import type { SessionStatus } from "@/shared/realtime/types";

const STATUSES: readonly string[] = [
  "running",
  "waiting_user",
  "paused",
  "completed",
  "failed",
  "cancelled",
];

/** Statut de session lu dans les détails d'un 409 (`council_not_waiting`, `council_not_failed`). */
export function statusIn(details: unknown): SessionStatus | null {
  const status = (details as { status?: unknown } | null)?.status;
  return typeof status === "string" && STATUSES.includes(status) ? (status as SessionStatus) : null;
}

/** Relit l'état d'une session (REST) et le montre : le direct a pu prendre de l'avance ou du retard. */
export async function rereadSession(sessionId: string): Promise<void> {
  try {
    const view = await fetchSession(sessionId);
    useSessionStore.getState().local(sessionId, { type: "snapshot", snapshot: snapshotOf(view) });
  } catch {
    // Le direct rattrapera : une relecture manquée n'est pas une erreur de plus à montrer.
  }
}
