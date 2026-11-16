import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveDraft } from "../api";
import { readableMessage } from "../errors";
import { projectKeys } from "../queryKeys";
import type { DraftKind } from "../types";

/**
 * Enregistrer un brouillon retouché (`PATCH /projects/{id}/drafts/{kind}`) : le serveur rend le
 * projet avec ses brouillons recontrôlés (un brouillon à vérifier modifié est relu), la page le
 * pose tel quel. `savingKind` : le brouillon en cours d'enregistrement.
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
    /** Le refus ou la panne du dernier enregistrement, et le brouillon qu'il concerne. */
    error: mutation.isError ? readableMessage(mutation.error) : null,
    errorKind: mutation.isError ? mutation.variables.kind : null,
  };
}
