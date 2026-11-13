import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { startReplan } from "../api";
import type { ReplanRequest } from "../types";

/** L'identifiant de la session déjà ouverte, dans le 409 `replan_open`. */
function openSessionOf(details: unknown): string | null {
  if (typeof details !== "object" || details === null) return null;
  const id = (details as Record<string, unknown>).session_id;
  return typeof id === "string" && id !== "" ? id : null;
}

/**
 * Lance la replanification d'un programme. Une replanification déjà ouverte (409 `replan_open`)
 * n'est pas une erreur : on suit sa session. Les autres refus (brouillon, programme inconnu)
 * s'affichent. Un seul départ à la fois (verrou posé de façon synchrone).
 */
export function useStartReplan(programId: string, onSession: (sessionId: string) => void) {
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (body: ReplanRequest) => startReplan(programId, body),
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
  return { start, pending: mutation.isPending, error };
}
