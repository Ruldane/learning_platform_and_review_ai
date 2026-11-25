import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveDraft } from "../api";
import { readableMessage } from "../errors";
import { projectKeys } from "../queryKeys";
import type { DraftKind } from "../types";

/**
 * Saves an edited draft (`PATCH /projects/{id}/drafts/{kind}`): the server returns the
 * project with its drafts re-checked (an edited draft to verify is re-read); the page uses it.
 * `savingKind`: the draft being saved.
 */
export function useSaveDraft(projectId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ kind, content }: { kind: DraftKind; content: string }) =>
      saveDraft(projectId, kind, content),
    onSuccess: (project) => {
      client.setQueryData(projectKeys.one(projectId), project);
    },
  });
  const { mutate } = mutation;
  return {
    save: (kind: DraftKind, content: string) => mutate({ kind, content }),
    savingKind: mutation.isPending ? mutation.variables.kind : null,
    /** The refusal or failure of the last save, and the draft it concerns. */
    error: mutation.isError ? readableMessage(mutation.error) : null,
    errorKind: mutation.isError ? mutation.variables.kind : null,
  };
}
