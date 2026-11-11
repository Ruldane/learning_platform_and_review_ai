import { useState } from "react";
import type { KeyTestResult } from "../types";
import type { TrackAction } from "./useActionError";
import { useDeleteApiKey } from "./useDeleteApiKey";
import { useSaveApiKey } from "./useSaveApiKey";
import { useTestApiKey } from "./useTestApiKey";

const ignore = () => undefined;

/** Actions sur les clés (enregistrer, supprimer, tester) et résultats de test par fournisseur. */
export function useKeyActions(track: TrackAction) {
  const save = useSaveApiKey();
  const remove = useDeleteApiKey();
  const test = useTestApiKey();
  const [testResults, setTestResults] = useState<Record<string, KeyTestResult>>({});

  const forget = (provider: string) =>
    setTestResults((previous) =>
      Object.fromEntries(Object.entries(previous).filter(([name]) => name !== provider)),
    );

  const pendingProvider =
    (save.isPending && save.variables?.provider) ||
    (remove.isPending && remove.variables) ||
    (test.isPending && test.variables) ||
    null;

  return {
    testResults,
    pendingProvider,
    /** Rejette si l'enregistrement échoue : la carte garde alors la saisie. */
    onSave: async (provider: string, key: string) => {
      await track(() => save.mutateAsync({ provider, key }));
      // La clé ne reste pas dans les variables de la mutation (conservées par le cache de TanStack).
      save.reset();
      forget(provider);
    },
    onDelete: (provider: string) => {
      track(() => remove.mutateAsync(provider)).then(() => forget(provider), ignore);
    },
    onTest: (provider: string) => {
      track(() => test.mutateAsync(provider)).then(
        (result) => setTestResults((previous) => ({ ...previous, [provider]: result })),
        ignore,
      );
    },
  };
}
