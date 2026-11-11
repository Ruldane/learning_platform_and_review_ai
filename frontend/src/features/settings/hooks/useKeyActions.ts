import { useRef, useState } from "react";
import type { KeyTestResult } from "../types";
import type { TrackAction } from "./useActionError";
import { useDeleteApiKey } from "./useDeleteApiKey";
import { useSaveApiKey } from "./useSaveApiKey";
import { useTestApiKey } from "./useTestApiKey";

const ignore = () => undefined;

/** Retire une occurrence de `provider` (deux enregistrements du même fournisseur peuvent se suivre). */
function without(list: string[], provider: string) {
  const index = list.indexOf(provider);
  return index < 0 ? list : [...list.slice(0, index), ...list.slice(index + 1)];
}

/** Actions sur les clés (enregistrer, supprimer, tester) et résultats de test par fournisseur. */
export function useKeyActions(track: TrackAction) {
  const save = useSaveApiKey();
  const remove = useDeleteApiKey();
  const test = useTestApiKey();
  const [testResults, setTestResults] = useState<Record<string, KeyTestResult>>({});
  // Enregistrements en cours, suivis ici : l'observateur de `save` ne voit que le dernier.
  const [saving, setSaving] = useState<string[]>([]);
  const lastSave = useRef(0);

  const forget = (provider: string) =>
    setTestResults((previous) =>
      Object.fromEntries(Object.entries(previous).filter(([name]) => name !== provider)),
    );

  const pendingProviders = [
    ...saving,
    ...(remove.isPending && remove.variables ? [remove.variables] : []),
    ...(test.isPending && test.variables ? [test.variables] : []),
  ];

  return {
    testResults,
    pendingProviders,
    /** Rejette si l'enregistrement échoue : la carte garde alors la saisie. */
    onSave: async (provider: string, key: string) => {
      const call = ++lastSave.current;
      setSaving((current) => [...current, provider]);
      try {
        await track(() => save.mutateAsync({ provider, key }));
        forget(provider);
      } finally {
        setSaving((current) => without(current, provider));
        // La clé ne reste pas dans les variables de la mutation (succès comme échec : l'erreur est
        // déjà copiée par `track`). Seulement si aucun enregistrement plus récent n'a pris le relais,
        // sinon on détacherait l'observateur d'une requête encore en vol.
        if (lastSave.current === call) save.reset();
      }
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
