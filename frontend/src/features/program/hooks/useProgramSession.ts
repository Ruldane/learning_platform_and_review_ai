import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { fetchSession } from "@/shared/realtime/sessionApi";
import { programKeys } from "../queryKeys";

const POLL_MS = 2000;

/**
 * The Strategist's session for a draft (`GET /sessions/{id}`): waiting for validation, or
 * revising or validating (re-read every 2 s while it runs). When its status changes,
 * the program is re-read: a revision wrote a version, a validation succeeded.
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
