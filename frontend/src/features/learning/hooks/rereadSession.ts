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
  "expired",
];

/** Session status read from the details of a 409 (`council_not_waiting`, `council_not_failed`). */
export function statusIn(details: unknown): SessionStatus | null {
  const status = (details as { status?: unknown } | null)?.status;
  return typeof status === "string" && STATUSES.includes(status) ? (status as SessionStatus) : null;
}

/** Re-reads a session's state (REST) and shows it: the live feed may be ahead or behind. */
export async function rereadSession(sessionId: string): Promise<void> {
  try {
    const view = await fetchSession(sessionId);
    useSessionStore.getState().local(sessionId, { type: "snapshot", snapshot: snapshotOf(view) });
  } catch {
    // The live feed will catch up: a missed re-read is not one more error to show.
  }
}
