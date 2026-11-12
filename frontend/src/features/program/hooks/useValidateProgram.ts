import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { validateProgram } from "../api";
import { programKeys } from "../queryKeys";
import { conflictNotice } from "./conflictNotice";

/**
 * « Valider le programme » (`POST /programs/{id}/validate`, D88). Un refus 422 (85 %, quiz,
 * pratique) est une erreur en ligne ; 409 `program_not_waiting` (révision en cours, second clic)
 * est une information. Dans tous les cas l'état du serveur est relu : programme et session.
 */
export function useValidateProgram(programId: string) {
  const client = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({ mutationFn: () => validateProgram(programId) });
  const { mutateAsync } = mutation;

  const validate = useCallback(async () => {
    setNotice(null);
    setError(null);
    try {
      await mutateAsync();
    } catch (failure) {
      const conflict = failure instanceof ApiError ? conflictNotice(failure) : null;
      if (conflict === null) setError(errorMessage(failure));
      else setNotice(conflict);
    }
    await Promise.all([
      client.invalidateQueries({ queryKey: programKeys.detail(programId) }),
      client.invalidateQueries({ queryKey: programKeys.sessions }),
    ]);
  }, [mutateAsync, client, programId]);

  return {
    validate,
    pending: mutation.isPending,
    validated: mutation.data?.status === "validated",
    notice,
    error,
  };
}
