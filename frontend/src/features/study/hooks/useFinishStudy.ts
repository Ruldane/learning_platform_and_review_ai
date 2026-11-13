import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { finishStudy } from "../api";
import { studyKeys } from "../queryKeys";

/**
 * « Terminer » : `PATCH /study-sessions/{id}` avec le temps travaillé en minutes entières. La
 * réponse (l'état de la session) remplace celle du cache. Un seul envoi à la fois, même pour deux
 * clics dans le même instant.
 */
export function useFinishStudy(studyId: string) {
  const queryClient = useQueryClient();
  const sending = useRef(false);
  const mutation = useMutation({
    mutationFn: (workedSeconds: number) => finishStudy(studyId, Math.round(workedSeconds / 60)),
    onSuccess: (session) => {
      queryClient.setQueryData(studyKeys.session(studyId), session);
      void queryClient.invalidateQueries({ queryKey: studyKeys.summary });
    },
  });
  const { mutateAsync } = mutation;
  const finish = async (workedSeconds: number): Promise<boolean> => {
    if (sending.current) return false;
    sending.current = true;
    try {
      await mutateAsync(workedSeconds);
      return true; // accepté : le verrou reste posé, « Terminer » ne part qu'une fois
    } catch {
      sending.current = false;
      return false; // l'erreur est affichée depuis la mutation
    }
  };
  return { finish, pending: mutation.isPending, error: mutation.error, reset: mutation.reset };
}
