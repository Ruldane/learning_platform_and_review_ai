import { useQueryClient } from "@tanstack/react-query";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { errorMessage } from "@/shared/api/errors";
import { putFiles } from "../api";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";
import { omit, type Files } from "./fileMaps";

/** Délai sans frappe avant l'enregistrement automatique (la frappe, elle, n'appelle personne). */
export const AUTOSAVE_MS = 1500;

/** Ce qui reste à envoyer une fois `sent` parti : une retouche faite pendant l'envoi est gardée. */
const withoutSent = (edits: Files, sent: Files): Files =>
  Object.fromEntries(Object.entries(edits).filter(([name, text]) => sent[name] !== text));

/** Enregistre 1,5 s après la dernière retouche (chaque retouche relance le délai). */
function useAutosave(dirty: boolean, edits: Files, save: () => Promise<boolean>) {
  useEffect(() => {
    if (!dirty) return undefined;
    const timer = setTimeout(() => void save(), AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [dirty, edits, save]);
}

interface Draft {
  edits: Files;
  /** Les fichiers en conflit avec Claude : ni envoyés ni écrasés tant que tu n'as pas choisi. */
  held: string[];
  server: Files;
}

/**
 * L'enregistrement des retouches : automatique après 1,5 s sans frappe, ou à la demande (`save`
 * attend un envoi en cours et rend vrai si tout est enregistré). Les fichiers en conflit avec Claude
 * ne partent pas : le serveur garde sa version, et `save` rend faux (le code à l'écran n'est pas
 * celui du serveur).
 */
export function useDraftSave(
  session: IdeSession,
  draft: Draft,
  setEdits: Dispatch<SetStateAction<Files>>,
  markMine: (files: Files) => void,
) {
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(draft);
  const inFlight = useRef<Promise<boolean> | null>(null);
  useEffect(() => {
    latest.current = draft;
  });
  const { id, entry } = session;
  const send = useCallback(
    async (sent: Files, mine: Files) => {
      setSaving(true);
      setError(null);
      try {
        const saved = await putFiles(id, sent, entry);
        queryClient.setQueryData(ideKeys.session(id), saved);
        markMine(mine);
        setEdits((current) => withoutSent(current, sent));
        return true;
      } catch (failure) {
        setError(errorMessage(failure));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [queryClient, id, entry, setEdits, markMine],
  );
  const save = useCallback(async () => {
    if (inFlight.current) await inFlight.current;
    const { edits, held, server } = latest.current;
    const sendable = omit(edits, held);
    let ok = true;
    if (Object.keys(sendable).length > 0) {
      inFlight.current = send({ ...server, ...sendable }, sendable);
      ok = await inFlight.current;
      inFlight.current = null;
    }
    return ok && held.length === 0;
  }, [send]);
  const dirty = Object.keys(draft.edits).length > 0;
  useAutosave(dirty, draft.edits, save);
  return { saving, error, save, dirty };
}
