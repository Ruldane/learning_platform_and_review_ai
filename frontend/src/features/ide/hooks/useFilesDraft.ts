import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { putFiles } from "../api";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";

/** Délai sans frappe avant l'enregistrement automatique (la frappe, elle, n'appelle personne). */
export const AUTOSAVE_MS = 1500;

type Files = Record<string, string>;

/** Ce qui reste à envoyer une fois `sent` parti : une retouche faite pendant l'envoi est gardée. */
const withoutSent = (edits: Files, sent: Files): Files =>
  Object.fromEntries(Object.entries(edits).filter(([name, text]) => sent[name] !== text));

/** Les retouches pas encore envoyées, par fichier, et les fichiers qu'elles donnent. */
function useEdits(session: IdeSession) {
  const [edits, setEdits] = useState<Files>({});
  const files = useMemo(() => ({ ...session.files, ...edits }), [session.files, edits]);
  const edit = useCallback(
    (name: string, text: string) =>
      setEdits((current) => {
        const rest = Object.fromEntries(Object.entries(current).filter(([key]) => key !== name));
        return text === session.files[name] ? rest : { ...rest, [name]: text };
      }),
    [session.files],
  );
  const discard = useCallback(() => setEdits({}), []);
  return { edits, files, edit, discard, setEdits };
}

/**
 * Les fichiers tels qu'on les édite : ce que le serveur a, plus les retouches pas encore
 * envoyées. Enregistre tout seul après 1,5 s sans frappe ; `save` attend un envoi en cours et rend
 * vrai si tout est enregistré (l'exécution l'appelle avant de partir). `discard` jette les
 * retouches quand le serveur a changé le fichier (proposition acceptée).
 */
export function useFilesDraft(session: IdeSession) {
  const queryClient = useQueryClient();
  const { edits, files, edit, discard, setEdits } = useEdits(session);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef({ files, edits });
  const inFlight = useRef<Promise<boolean> | null>(null);
  useEffect(() => {
    latest.current = { files, edits };
  });
  const send = useCallback(
    async (sent: Files) => {
      setSaving(true);
      setError(null);
      try {
        const saved = await putFiles(session.id, sent, session.entry);
        queryClient.setQueryData(ideKeys.session(session.id), saved);
        setEdits((current) => withoutSent(current, sent));
        return true;
      } catch (failure) {
        setError(errorMessage(failure));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [queryClient, session.id, session.entry, setEdits],
  );
  const save = useCallback(async () => {
    if (inFlight.current) await inFlight.current;
    const { files: sent, edits: pending } = latest.current;
    if (Object.keys(pending).length === 0) return true;
    inFlight.current = send(sent);
    const ok = await inFlight.current;
    inFlight.current = null;
    return ok;
  }, [send]);
  const dirty = Object.keys(edits).length > 0;
  useEffect(() => {
    if (!dirty) return undefined;
    const timer = setTimeout(() => void save(), AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [dirty, edits, save]);
  return { files, dirty, saving, error, edit, save, discard };
}
