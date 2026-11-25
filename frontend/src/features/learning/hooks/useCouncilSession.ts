import { useMemo } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { councilStage } from "../councilStage";
import { programLink } from "../programLink";
import type { GoalOut } from "../types";
import { useDebateRounds } from "./useDebateRounds";
import { useGoal } from "./useGoal";

/**
 * The Council session followed live (resumed after a reload: the id comes from
 * the goal, the stream replays the events) and, once the path is chosen, the session of the
 * program. The stage is derived from the events; while the program has no session,
 * the goal is re-read every 2 s. `programFailed`: the program session failed without
 * a program being saved (the same choice restarts it).
 */
export function useCouncilSession(
  initial: GoalOut,
  sessionId: string,
  createSocket?: SocketFactory,
) {
  const stream = useSessionStream(sessionId, { createSocket });
  const actions = useSessionActions(sessionId);
  const debateRounds = useDebateRounds();
  const { events } = stream;

  const chosen = useMemo(
    () => councilStage(events, false, debateRounds).stage === "program",
    [events, debateRounds],
  );
  const goal = useGoal(initial.id, chosen).data ?? initial;
  const hasProgram = goal.program_session_id !== null || goal.program_id !== null;
  const progress = useMemo(
    () => councilStage(events, hasProgram, debateRounds),
    [events, hasProgram, debateRounds],
  );

  const programStream = useSessionStream(goal.program_session_id, { createSocket });
  const link = useMemo(
    () => programLink(programStream.events, goal.program_id),
    [programStream.events, goal.program_id],
  );
  const programFailed = programStream.status === "failed" && goal.program_id === null && !link;
  return { goal, stream, actions, progress, programLink: link, programFailed };
}
