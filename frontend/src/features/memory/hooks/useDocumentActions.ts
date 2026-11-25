import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import type { RunSource } from "@/shared/lib/runSource";
import { markLearned, uploadDocument } from "../api";
import { memoryKeys } from "../queryKeys";
import { invalidateMemory } from "./useItemMutations";
import { useLearnings } from "./useLearnings";

export type { Learning } from "./useLearnings";

/**
 * Actions of the Documents screen: import (file, link, pasted text) and « déjà appris ».
 * `sent` grows with each successful import, duplicates included: the screen uses it as a `key` to
 * reset the link and pasted-text forms (a failure keeps the input).
 * The Archivist sessions still running on the server (read once on mount) complete
 * `learnings` after a reload, never overwriting a local entry.
 */
export function useDocumentActions() {
  const queryClient = useQueryClient();
  const [sent, setSent] = useState(0);
  const { learnings, start, finish } = useLearnings();

  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async () => {
      setSent((n) => n + 1);
      await queryClient.invalidateQueries({ queryKey: memoryKeys.documents });
    },
  });

  const learn = useMutation({
    mutationFn: ({ documentId, source }: { documentId: string; source?: RunSource }) =>
      markLearned(documentId, source),
    onSuccess: ({ session_id: sessionId }, { documentId }) => start(documentId, sessionId),
  });

  /** The Archivist is done: the acquired items, statistics, map and documents are re-read. */
  const finishLearning = useCallback(
    (documentId: string) => {
      finish(documentId);
      void invalidateMemory(queryClient);
    },
    [finish, queryClient],
  );

  const requesting = learn.isPending ? [learn.variables.documentId] : [];
  const running = learnings.filter((entry) => !entry.finished).map((entry) => entry.documentId);
  return {
    upload,
    learn,
    sent,
    duplicate: upload.isSuccess && upload.data.duplicate,
    learnings,
    learningIds: [...requesting, ...running],
    finishLearning,
  };
}
