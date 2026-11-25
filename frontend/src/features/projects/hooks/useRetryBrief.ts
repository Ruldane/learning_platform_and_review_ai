import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { useLaunchSource } from "@/shared/session-ui";
import { retryBrief } from "../api";
import { readableMessage } from "../errors";
import { projectKeys } from "../queryKeys";
import type { ProjectOut } from "../types";

/**
 * « Réessayer l'énoncé » (`POST /projects/{id}/brief`, 202): the project goes back to
 * `brief_pending` and the page re-reads it to follow the new session. 409 `brief_not_failed`:
 * been retried; the page re-reads to show the real state.
 */
export function useRetryBrief(projectId: string, onRetried?: () => void) {
  const client = useQueryClient();
  const provider = useLaunchSource();
  const sending = useRef(false);
  const mutation = useMutation({
    mutationFn: () => retryBrief(projectId, provider.source),
    onSettled: () => client.invalidateQueries({ queryKey: projectKeys.one(projectId) }),
  });
  const { mutateAsync } = mutation;
  return {
    retry: () => {
      const status = client.getQueryData<ProjectOut>(projectKeys.one(projectId))?.status;
      if (sending.current || (status !== undefined && status !== "brief_failed")) return;
      sending.current = true;
      void mutateAsync()
        .then(() => onRetried?.())
        .catch(() => null)
        .finally(() => {
          sending.current = false;
        });
    },
    launchMenu: provider.menu,
    pending: mutation.isPending,
    error: mutation.isError ? readableMessage(mutation.error) : null,
  };
}
