import { useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from "react";
import type { IdeSession } from "../types";
import { omit, type Files } from "./fileMaps";
import { useSendFiles } from "./useSendFiles";

/** Idle time before automatic save (typing itself calls no one). */
export const AUTOSAVE_MS = 1500;

/** Saves 1.5 s after the last edit (each edit restarts the delay). */
function useAutosave(dirty: boolean, edits: Files, server: Files, save: () => Promise<boolean>) {
  useEffect(() => {
    if (!dirty) return undefined;
    const timer = setTimeout(() => void save(), AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [dirty, edits, server, save]); // the re-read session restarts the attempt (after a refusal)
}

interface Draft {
  edits: Files;
  /** Files in conflict with Claude: neither sent nor overwritten until you choose. */
  held: string[];
  server: Files;
  /** The fingerprints (sha256) of the files as the server gave them at the last read. */
  hashes: Files;
}

/**
 * Saving edits: automatic after 1.5 s without typing, or on demand (`save`
 * waits for a send and returns true if all is saved). Files in conflict with Claude
 * are not sent: the server keeps its version, and `save` returns false (the code on screen is not
 * the server's).
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
