import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { fetchSession } from "@/shared/realtime/sessionApi";
import { programKeys } from "../queryKeys";

const POLL_MS = 2000;

/**
 * La session du Stratège d'un brouillon (`GET /sessions/{id}`) : en attente de la validation, ou en
 * train de réviser / valider (relue toutes les 2 s tant qu'elle tourne). Quand son statut change,
 * le programme est relu : une révision a écrit une version, une validation a abouti.
 */
export function useProgramSession(sessionId: string | null, enabled: boolean, programId: string) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: programKeys.session(sessionId ?? "none"),
    queryFn: ({ signal }) => fetchSession(sessionId ?? "", signal),
    enabled: sessionId !== null && enabled,
    refetchInterval: (state) => (state.state.data?.status === "running" ? POLL_MS : false),
  });
  const status = query.data?.status;
  const previous = useRef(status);
  useEffect(() => {
    if (previous.current !== undefined && status !== undefined && previous.current !== status) {
      void client.invalidateQueries({ queryKey: programKeys.detail(programId) });
    }
    previous.current = status;
  }, [status, client, programId]);
  return query;
}
