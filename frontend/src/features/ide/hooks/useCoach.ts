import { useCallback, useEffect, useRef } from "react";
import type { RunSource } from "@/shared/lib/runSource";
import { isFailedRun } from "../toView";
import type { RunProgress, TeachIn } from "../types";
import { useTeach } from "./useTeach";

/** Où en est la personne dans le code : joint à chaque appel pour que le professeur situe l'aide. */
export interface Where {
  filePath: string;
  line: number | null;
}

/** Les champs d'un appel que l'appelant choisit ; l'emplacement est ajouté ici. */
export type Ask = Pick<TeachIn, "trigger" | "question" | "run_id">;

/**
 * Les gestes qui réveillent le professeur, et eux seuls. `ask` part sur un geste (Indice,
 * Pourquoi, question, minuterie). `afterRun` part à la fin d'une exécution **en échec** et une
 * seule fois par exécution, et seulement si le mode automatique est ouvert (`automatic`) : plafond
 * atteint, mode « sur demande » ou réglages pas encore lus, aucun appel ne part tout seul.
 */
export function useCoach(sessionId: string, automatic: boolean, where: Where) {
  const teach = useTeach(sessionId);
  const handled = useRef(new Set<string>());
  const latest = useRef({ automatic, where });
  useEffect(() => {
    latest.current = { automatic, where };
  });
  const { mutate, mutateAsync } = teach;
  const ask = useCallback(
    (what: Ask, source?: RunSource) => {
      const { filePath, line } = latest.current.where;
      mutate({ ...what, file_path: filePath, line, source });
    },
    [mutate],
  );
  /** Une question tapée : `true` si le professeur la prend (sinon la saisie reste à sa place). */
  const sendQuestion = useCallback(
    async (question: string, runId: string | null, source?: RunSource): Promise<boolean> => {
      const { filePath, line } = latest.current.where;
      try {
        const out = await mutateAsync({
          trigger: "question",
          question,
          run_id: runId,
          file_path: filePath,
          line,
          source,
        });
        return !out.skipped;
      } catch {
        return false; // l'erreur est lue dans `teach.error`
      }
    },
    [mutateAsync],
  );
  const afterRun = useCallback(
    (run: RunProgress) => {
      if (!isFailedRun(run) || !latest.current.automatic || handled.current.has(run.id)) return;
      handled.current.add(run.id);
      ask({ trigger: "run_error", run_id: run.id });
    },
    [ask],
  );
  return { teach, ask, sendQuestion, afterRun };
}
