import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { markLearned, uploadDocument } from "../api";
import { memoryKeys } from "../queryKeys";
import { invalidateMemory } from "./useItemMutations";

/** Un marquage « déjà appris » lancé : la session de l'Archiviste à suivre pour ce document. */
export interface Learning {
  documentId: string;
  sessionId: string;
  finished: boolean;
}

/**
 * Actions de l'écran Documents : importer (fichier, lien, texte collé) et « déjà appris ».
 * `sent` croît à chaque import réussi, doublon compris : l'écran s'en sert comme `key` pour
 * remettre à zéro les formulaires du lien et du texte collé (un échec garde la saisie).
 */
export function useDocumentActions() {
  const queryClient = useQueryClient();
  const [sent, setSent] = useState(0);
  const [learnings, setLearnings] = useState<Learning[]>([]);

  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async () => {
      setSent((n) => n + 1);
      await queryClient.invalidateQueries({ queryKey: memoryKeys.documents });
    },
  });

  const learn = useMutation({
    mutationFn: markLearned,
    onSuccess: ({ session_id: sessionId }, documentId) =>
      setLearnings((all) => [
        ...all.filter((entry) => entry.documentId !== documentId),
        { documentId, sessionId, finished: false },
      ]),
  });

  /** L'Archiviste a fini : les acquis, les statistiques, la carte et les documents sont relus. */
  const finishLearning = useCallback(
    (documentId: string) => {
      setLearnings((all) =>
        all.map((entry) =>
          entry.documentId === documentId ? { ...entry, finished: true } : entry,
        ),
      );
      void invalidateMemory(queryClient);
    },
    [queryClient],
  );

  const requesting = learn.isPending ? [learn.variables] : [];
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
