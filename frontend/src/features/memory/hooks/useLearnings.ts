import { useCallback, useMemo, useState } from "react";
import { useRunningLearnings } from "./useRunningLearnings";

/** A started « déjà appris » marking: the Archivist session to follow for this document. */
export interface Learning {
  documentId: string;
  sessionId: string;
  finished: boolean;
}

/**
 * The Archivist tracking on the Documents screen: those started here (`start`, `finish`) and those
 * still running on the server (read once on mount), which resume tracking after a
 * reload. A local entry always wins over the server's; a resumed tracking that
 * finishes becomes a finished local entry, which a re-read does not bring back.
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
