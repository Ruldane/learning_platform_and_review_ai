import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { studySessionPath } from "@/shared/lib/studyRoutes";
import { startStudy } from "../api";
import { openSessionIn } from "../toView";
import type { StudyStart } from "../types";

/**
 * Départ d'une session : ouvre la session puis va sur sa page. Une session déjà ouverte (409
 * `study_already_open`, ou 200 pour la même leçon) n'est pas une erreur : on y va. 404
 * `no_block_today` : `noBlock`, pour proposer de choisir une leçon (et `onNoBlock`, s'il est
 * donné). Un seul départ à la fois.
 */
export function useStartStudy(onNoBlock?: () => void) {
  const launch = useLaunchSource();
  const navigate = useNavigate();
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [noBlock, setNoBlock] = useState(false);
  const mutation = useMutation({
    mutationFn: (body: StudyStart) => startStudy(body, launch.source),
  });
  const { mutateAsync } = mutation;

  const start = async (body: StudyStart): Promise<void> => {
    if (sending.current) return;
    sending.current = true;
    setError(null);
    setNoBlock(false);
    try {
      const started = await mutateAsync(body);
      void navigate(studySessionPath(started.study_session_id));
      return; // la page se quitte : le verrou reste posé, un second clic ne rouvre rien
    } catch (failure) {
      const details = failure instanceof ApiError ? failure.details : null;
      const open =
        failure instanceof ApiError && failure.code === "study_already_open"
          ? openSessionIn(details)
          : null;
      if (open) {
        const kind = (details as { kind?: unknown } | null)?.kind;
        void navigate(studySessionPath(open, kind));
        return;
      }
      if (failure instanceof ApiError && failure.code === "no_block_today") {
        setNoBlock(true);
        onNoBlock?.();
      } else setError(errorMessage(failure));
    }
    sending.current = false;
  };
  return { start, pending: mutation.isPending, error, noBlock, launchMenu: launch.menu };
}
