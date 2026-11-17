import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createSession, fetchSessions } from "../api";
import { ideKeys } from "../queryKeys";

/** Mes séances de code (`GET /ide/sessions`), pour l'état des exercices. */
export function useSessions() {
  return useQuery({
    queryKey: ideKeys.sessions,
    queryFn: ({ signal }) => fetchSessions(signal),
  });
}

/** Ouvre une séance sur un exercice (`null` : séance libre) ; rend la séance créée. */
export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (exerciseId: string | null) => createSession(exerciseId),
    onSuccess: (session) => {
      queryClient.setQueryData(ideKeys.session(session.id), session);
      return queryClient.invalidateQueries({ queryKey: ideKeys.sessions });
    },
  });
}
