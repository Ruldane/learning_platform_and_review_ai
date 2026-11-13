import { useQuery } from "@tanstack/react-query";
import { listSessions } from "@/shared/realtime/sessionApi";
import { programKeys } from "../queryKeys";

/**
 * La replanification de ce programme qui attend une réponse (`GET /sessions?graph=replan&
 * status=waiting_user`, sujet = programme) : son identifiant, ou `null`. Lue seulement pour un
 * programme validé (un brouillon ne se replanifie pas).
 */
export function useWaitingReplan(programId: string, enabled: boolean) {
  return useQuery({
    queryKey: programKeys.waitingReplan(programId),
    queryFn: async ({ signal }) => {
      const sessions = await listSessions("replan", "waiting_user", signal);
      const mine = sessions.find(
        (session) => session.subject_type === "program" && session.subject_id === programId,
      );
      return mine?.id ?? null;
    },
    enabled,
    staleTime: 0,
  });
}
