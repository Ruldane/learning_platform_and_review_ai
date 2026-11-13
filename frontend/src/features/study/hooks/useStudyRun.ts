import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { studyKeys } from "../queryKeys";
import type { StudySessionOut } from "../types";
import { useFinishStudy } from "./useFinishStudy";

interface StudyRunOptions {
  session: StudySessionOut;
  /** « Terminer » a été accepté : le Tuteur conclut. */
  finishing: boolean;
  onFinishing: () => void;
  createSocket?: SocketFactory;
}

const OVER = ["completed", "failed", "cancelled"] as const;

/**
 * Une session d'étude en cours : le flux du Tuteur (seulement quand la session d'agents vit), les
 * actions de session par REST, le temps travaillé (lu à l'envoi, jamais recopié à chaque seconde)
 * et « Terminer ». « Terminer » n'est possible que lorsque le Tuteur attend une réponse
 * (`waiting_user`, sinon 409) ou que sa session s'est arrêtée (`interrupted` : le temps est rangé).
 */
export function useStudyRun({ session, finishing, onFinishing, createSocket }: StudyRunOptions) {
  const queryClient = useQueryClient();
  const live = session.status === "open" && session.session_id !== null;
  const stream = useSessionStream(live ? session.session_id : null, { createSocket });
  const actions = useSessionActions(session.session_id ?? "");
  const finisher = useFinishStudy(session.id);
  const worked = useRef(0);

  // La session d'agents s'est terminée : l'état de la session d'étude a changé (bilan, arrêt).
  const over = live && (OVER as readonly string[]).includes(stream.status);
  useEffect(() => {
    if (over) void queryClient.invalidateQueries({ queryKey: studyKeys.session(session.id) });
  }, [over, queryClient, session.id]);

  const waiting = session.status === "interrupted" || (live && stream.status === "waiting_user");
  const canFinish = waiting && !finishing && !finisher.pending;
  const finish = async () => {
    if (await finisher.finish(worked.current)) onFinishing();
  };
  return {
    stream,
    actions,
    canFinish,
    finish,
    finishError: finisher.error,
    finishPending: finisher.pending,
    onWorkedChange: (seconds: number) => {
      worked.current = seconds;
    },
  };
}

export type StudyRun = ReturnType<typeof useStudyRun>;
