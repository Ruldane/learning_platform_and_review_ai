import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { startReplan } from "../api";
import type { ReplanRequest } from "../types";

/** The identifier of the session already open, in the 409 `replan_open`. */
function openSessionOf(details: unknown): string | null {
  if (typeof details !== "object" || details === null) return null;
  const id = (details as Record<string, unknown>).session_id;
  return typeof id === "string" && id !== "" ? id : null;
}

/**
 * Starts a program's replan. A replan already open (409 `replan_open`) is not an error:
 * its session is followed. Other refusals (draft, unknown program) are shown. One start at a
 * time (lock set synchronously).
 */
export function useStartReplan(programId: string, onSession: (sessionId: string) => void) {
  const launch = useLaunchSource();
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (body: ReplanRequest) => startReplan(programId, body, launch.source),
  });
  const { mutateAsync } = mutation;

  const start = async (body: ReplanRequest): Promise<void> => {
    if (sending.current) return;
    sending.current = true;
    setError(null);
    try {
      onSession((await mutateAsync(body)).session_id);
    } catch (failure) {
      const open =
        failure instanceof ApiError && failure.code === "replan_open"
          ? openSessionOf(failure.details)
          : null;
      if (open) onSession(open);
      else setError(errorMessage(failure));
    }
    sending.current = false;
  };
  return { start, pending: mutation.isPending, error, launchMenu: launch.menu };
}
