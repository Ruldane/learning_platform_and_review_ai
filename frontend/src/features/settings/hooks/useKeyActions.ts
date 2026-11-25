import { useRef, useState } from "react";
import type { KeyTestResult } from "../types";
import type { TrackAction } from "./useActionError";
import { useDeleteApiKey } from "./useDeleteApiKey";
import { useSaveApiKey } from "./useSaveApiKey";
import { useTestApiKey } from "./useTestApiKey";

const ignore = () => undefined;

/** Removes one occurrence of `provider` (two saves of the same provider can follow each other). */
function without(list: string[], provider: string) {
  const index = list.indexOf(provider);
  return index < 0 ? list : [...list.slice(0, index), ...list.slice(index + 1)];
}

/** Key actions (save, delete, test) and test results per provider. */
export function useKeyActions(track: TrackAction) {
  const save = useSaveApiKey();
  const remove = useDeleteApiKey();
  const test = useTestApiKey();
  const [testResults, setTestResults] = useState<Record<string, KeyTestResult>>({});
  // Saves in progress, tracked here: the `save` observer only sees the latest one.
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
    /** Rejects if the save fails: the card then keeps the input. */
    onSave: async (provider: string, key: string) => {
      const call = ++lastSave.current;
      setSaving((current) => [...current, provider]);
      try {
        await track(() => save.mutateAsync({ provider, key }));
        forget(provider);
      } finally {
        setSaving((current) => without(current, provider));
        // The key does not stay in the mutation's variables (on success as on failure: the error is
        // already copied by `track`). Only if no more recent save has taken over,
        // otherwise we would detach the observer from a request still in flight.
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
