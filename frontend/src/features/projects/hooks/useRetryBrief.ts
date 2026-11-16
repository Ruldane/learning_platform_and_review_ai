import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { retryBrief } from "../api";
import { readableMessage } from "../errors";
import { projectKeys } from "../queryKeys";
import type { ProjectOut } from "../types";

/**
 * « Réessayer l'énoncé » (`POST /projects/{id}/brief`, 202) : le projet repasse à `brief_pending` et
 * la page relit le projet pour suivre la nouvelle session. 409 `brief_not_failed` : l'énoncé a déjà
 * été relancé, la page se relit pour montrer l'état réel.
 */
export function useRetryBrief(projectId: string) {
  const client = useQueryClient();
  const sending = useRef(false);
  const mutation = useMutation({
    mutationFn: () => retryBrief(projectId),
    onSettled: () => client.invalidateQueries({ queryKey: projectKeys.one(projectId) }),
  });
  const { mutateAsync } = mutation;
  return {
    retry: () => {
      const status = client.getQueryData<ProjectOut>(projectKeys.one(projectId))?.status;
      if (sending.current || (status !== undefined && status !== "brief_failed")) return;
      sending.current = true;
      void mutateAsync()
        .catch(() => null)
        .finally(() => {
          sending.current = false;
        });
    },
    pending: mutation.isPending,
    error: mutation.isError ? readableMessage(mutation.error) : null,
  };
}
