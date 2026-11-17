import { useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from "react";
import type { IdeSession } from "../types";
import { omit, type Files } from "./fileMaps";
import { useSendFiles } from "./useSendFiles";

/** Délai sans frappe avant l'enregistrement automatique (la frappe, elle, n'appelle personne). */
export const AUTOSAVE_MS = 1500;

/** Enregistre 1,5 s après la dernière retouche (chaque retouche relance le délai). */
function useAutosave(dirty: boolean, edits: Files, server: Files, save: () => Promise<boolean>) {
  useEffect(() => {
    if (!dirty) return undefined;
    const timer = setTimeout(() => void save(), AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [dirty, edits, server, save]); // la séance relue relance l'essai (après un refus)
}

interface Draft {
  edits: Files;
  /** Les fichiers en conflit avec Claude : ni envoyés ni écrasés tant que tu n'as pas choisi. */
  held: string[];
  server: Files;
  /** Les empreintes (sha256) des fichiers tels que le serveur les a donnés à la dernière lecture. */
  hashes: Files;
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
  const latest = useRef(draft);
  const inFlight = useRef<Promise<boolean> | null>(null);
  useEffect(() => {
    latest.current = draft;
  });
  const hashesOf = useCallback(() => latest.current.hashes, []);
  const { send, saving, error } = useSendFiles(session, hashesOf, setEdits, markMine);
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
  useAutosave(dirty, draft.edits, draft.server, save);
  return { saving, error, save, dirty };
}
