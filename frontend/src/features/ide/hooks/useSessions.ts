import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createSession, fetchSessions } from "../api";
import { ideKeys } from "../queryKeys";

/** My code sessions (`GET /ide/sessions`), for the exercises' state. */
export function useSessions() {
  return useQuery({
    queryKey: ideKeys.sessions,
    queryFn: ({ signal }) => fetchSessions(signal),
  });
}

/** Opens a session on an exercise (`null`: free session); returns the created session. */
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
