import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { errorMessage } from "@/shared/api/errors";
import { patchResource } from "../api";
import { lessonsKeys } from "../queryKeys";
import type { ResourceStatus } from "../types";

/**
 * « Lue » / « À lire » (`PATCH /resources/{id}`). Lessons and the library are re-read after
 * each change; a failure is reported in `error`.
 */
export function useResourceStatus() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ resourceId, status }: { resourceId: string; status: ResourceStatus }) =>
      patchResource(resourceId, status),
    onSettled: () => client.invalidateQueries({ queryKey: lessonsKeys.all }),
  });
  const { mutate } = mutation;
  const setStatus = useCallback(
    (resourceId: string, status: ResourceStatus) => mutate({ resourceId, status }),
    [mutate],
  );
  return { setStatus, error: mutation.error ? errorMessage(mutation.error) : null };
}
