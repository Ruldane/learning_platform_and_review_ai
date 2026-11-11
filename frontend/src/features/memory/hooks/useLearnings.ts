import { useCallback, useMemo, useState } from "react";
import { useRunningLearnings } from "./useRunningLearnings";

/** Un marquage « déjà appris » lancé : la session de l'Archiviste à suivre pour ce document. */
export interface Learning {
  documentId: string;
  sessionId: string;
  finished: boolean;
}

/**
 * Les suivis de l'Archiviste de l'écran Documents : ceux lancés ici (`start`, `finish`) et ceux
 * encore en cours côté serveur (lus une fois au montage), qui reprennent le suivi après un
 * rechargement. Une entrée locale prime toujours sur celle du serveur ; un suivi repris qui se
 * termine devient une entrée locale terminée, que la relecture ne fait pas revenir.
 */
export function useLearnings() {
  const [local, setLocal] = useState<Learning[]>([]);
  const resumed = useRunningLearnings().data;
  const learnings = useMemo(
    () => [
      ...local,
      ...(resumed ?? [])
        .filter((run) => !local.some((entry) => entry.documentId === run.documentId))
        .map((run) => ({ ...run, finished: false })),
    ],
    [local, resumed],
  );

  const start = useCallback(
    (documentId: string, sessionId: string) =>
      setLocal((all) => [
        ...all.filter((entry) => entry.documentId !== documentId),
        { documentId, sessionId, finished: false },
      ]),
    [],
  );

  const finish = useCallback(
    (documentId: string) => {
      const run = resumed?.find((entry) => entry.documentId === documentId);
      setLocal((all) =>
        all.some((entry) => entry.documentId === documentId) || !run
          ? all.map((entry) =>
              entry.documentId === documentId ? { ...entry, finished: true } : entry,
            )
          : [...all, { ...run, finished: true }],
      );
    },
    [resumed],
  );

  return { learnings, start, finish };
}
