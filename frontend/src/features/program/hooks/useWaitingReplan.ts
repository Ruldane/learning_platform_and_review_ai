import { useQuery } from "@tanstack/react-query";
import { listSessions } from "@/shared/realtime/sessionApi";
import { programKeys } from "../queryKeys";

/**
 * The replan of this program waiting for an answer (`GET /sessions?graph=replan&
 * status=waiting_user`, subject = program): its identifier, or `null`. Read only for a
 * validated program (a draft is never replanned).
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
