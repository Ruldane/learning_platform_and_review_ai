import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { markLearned, uploadDocument } from "../api";
import { memoryKeys } from "../queryKeys";
import { invalidateMemory } from "./useItemMutations";
import { useLearnings } from "./useLearnings";

export type { Learning } from "./useLearnings";

/**
 * Actions de l'écran Documents : importer (fichier, lien, texte collé) et « déjà appris ».
 * `sent` croît à chaque import réussi, doublon compris : l'écran s'en sert comme `key` pour
 * remettre à zéro les formulaires du lien et du texte collé (un échec garde la saisie).
 * Les sessions de l'Archiviste encore en cours côté serveur (lues une fois au montage) complètent
 * `learnings` après un rechargement, sans jamais écraser une entrée locale.
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
    mutationFn: markLearned,
    onSuccess: ({ session_id: sessionId }, documentId) => start(documentId, sessionId),
  });

  /** L'Archiviste a fini : les acquis, les statistiques, la carte et les documents sont relus. */
  const finishLearning = useCallback(
    (documentId: string) => {
      finish(documentId);
      void invalidateMemory(queryClient);
    },
    [finish, queryClient],
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
