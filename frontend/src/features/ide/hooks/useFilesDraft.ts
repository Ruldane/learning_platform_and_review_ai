import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";
import { omit, type Files } from "./fileMaps";
import { useClaudeChanges } from "./useClaudeChanges";
import { AUTOSAVE_MS, useDraftSave } from "./useDraftSave";

export { AUTOSAVE_MS };

/**
 * The files as they are edited: what the server has, plus the edits not yet
 * sent. Saves on its own after 1.5 s without typing; `save` waits for a send and returns
 * true if everything is saved (the run calls it before starting). `discard` drops the
 * edits when the server changed the file (accepted proposal).
 *
 * The session is re-read live: if Claude changes a file on the server, the editor loads it
 * and says so (`claude.notices`); if you had unsaved edits on that file, they
 * are kept, nothing is sent for it, and you choose (`claude.conflicts`): never a silent
 * loss, in either direction.
 */
export function useFilesDraft(session: IdeSession) {
  const queryClient = useQueryClient();
  const [edits, setEdits] = useState<Files>({});
  const { conflicts, notices, acknowledge, markMine } = useClaudeChanges(session.files, edits);
  const held = useMemo(() => Object.keys(conflicts), [conflicts]);
  const saver = useDraftSave(
    session,
    { edits, held, server: session.files, hashes: session.file_hashes },
    setEdits,
    markMine,
  );
  const files = useMemo(() => ({ ...session.files, ...edits }), [session.files, edits]);
  const edit = useCallback(
    (name: string, text: string) => {
      // You write to a file Claude just changed: you start from its version, with no conflict.
      if (!(name in edits)) acknowledge([name]);
      setEdits((current) => {
        const rest = omit(current, [name]);
        return text === session.files[name] ? rest : { ...rest, [name]: text };
      });
    },
    [edits, acknowledge, session.files],
  );
  const discard = useCallback(() => {
    setEdits({});
    const fresh = queryClient.getQueryData<IdeSession>(ideKeys.session(session.id));
    if (fresh) markMine(fresh.files);
  }, [queryClient, session.id, markMine]);
  const claude = useMemo(
    () => ({
      conflicts,
      notices,
      dismiss: (name: string) => acknowledge([name]),
      keepMine: (name: string) => acknowledge([name]),
      takeTheirs: (name: string) => setEdits((current) => omit(current, [name])),
    }),
    [conflicts, notices, acknowledge],
  );
  return { files, edit, discard, claude, ...saver };
}
