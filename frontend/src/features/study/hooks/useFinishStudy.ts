import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { finishStudy } from "../api";
import { studyKeys } from "../queryKeys";

/**
 * « Terminer »: `PATCH /study-sessions/{id}` with the worked time in whole minutes. The
 * response (the session's state) replaces the cached one. Only one send at a time, even for two
 * clicks at the same moment.
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
      return true; // accepted: the lock stays set, « Terminer » goes out only once
    } catch {
      sending.current = false;
      return false; // the error is shown from the mutation
    }
  };
  return { finish, pending: mutation.isPending, error: mutation.error, reset: mutation.reset };
}
