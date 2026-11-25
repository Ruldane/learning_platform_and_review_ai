import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { retryCouncil } from "../api";
import { learningKeys } from "../queryKeys";
import { rereadSession, statusIn } from "./rereadSession";

function conflictNotice(failure: ApiError): string | null {
  if (failure.code === "goal_already_chosen") return t("learning.retry.alreadyChosen");
  if (failure.code !== "council_not_failed") return null;
  const status = statusIn(failure.details);
  return status === null
    ? t("learning.retry.notFailed")
    : t("learning.retry.notFailedStatus", { status: t(`session.status.${status}`) });
}

/**
 * Restarts a failed Council (`POST /goals/{id}/council`). The 202 returns the goal with its
 * new session: the page follows it (it remounts on `council_session_id`), the proposals
 * start from zero and the boards of the old Council are no longer shown. The 409 refusals
 * (`council_not_failed`, `goal_already_chosen`) are reported in `notice`, then the goal and the
 * session are re-read; the rest goes to `error`.
 */
export function useRetryCouncil(goalId: string, sessionId: string) {
  const client = useQueryClient();
  const { menu: launchMenu, source } = useLaunchSource();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (choice: RunSource | undefined) => retryCouncil(goalId, choice),
  });
  const { mutateAsync } = mutation;

  const retry = useCallback(async () => {
    setNotice(null);
    setError(null);
    try {
      const started = await mutateAsync(source);
      // Nothing from the old batch or old board, not even for a moment.
      await client.resetQueries({ queryKey: learningKeys.proposals(goalId) });
      client.setQueryData(learningKeys.goal(goalId), started.goal);
      void client.invalidateQueries({ queryKey: learningKeys.boards(goalId) });
    } catch (failure) {
      const conflict = failure instanceof ApiError ? conflictNotice(failure) : null;
      if (conflict === null) return setError(errorMessage(failure));
      setNotice(conflict);
      await Promise.all([
        client.invalidateQueries({ queryKey: learningKeys.goal(goalId) }),
        rereadSession(sessionId),
      ]);
    }
  }, [client, goalId, sessionId, mutateAsync, source]);

  return { retry, launchMenu, pending: mutation.isPending, notice, error };
}
