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
 * La session du Conseil suivie en direct (reprise après rechargement : l'identifiant vient de
 * l'objectif, le flux rejoue les événements) et, une fois le parcours choisi, la session du
 * programme. L'étape se déduit des événements ; tant que le programme n'a pas de session,
 * l'objectif est relu toutes les 2 s. `programFailed` : la session du programme a échoué sans
 * qu'un programme soit enregistré (le même choix la relance).
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
