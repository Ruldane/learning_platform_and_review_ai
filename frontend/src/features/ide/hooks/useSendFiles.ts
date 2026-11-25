import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState, type Dispatch, type SetStateAction } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { putFiles } from "../api";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";
import { pick, type Files } from "./fileMaps";

/** What is left to send once `sent` has gone: an edit made during the send is kept. */
const withoutSent = (edits: Files, sent: Files): Files =>
  Object.fromEntries(Object.entries(edits).filter(([name, text]) => sent[name] !== text));

/**
 * Sends the files to the server, with the fingerprint of the version each was edited from
 * (`hashesOf`, read at send time): if Claude has written since (409 `stale_base`), nothing is
 * saved, the session is re-read, and the choice (keep yours, take theirs) appears for
 * the files concerned.
 */
export function useSendFiles(
  session: IdeSession,
  hashesOf: () => Files,
  setEdits: Dispatch<SetStateAction<Files>>,
  markMine: (files: Files) => void,
) {
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { id, entry } = session;
  const send = useCallback(
    async (sent: Files, mine: Files) => {
      setSaving(true);
      setError(null);
      try {
        // A re-read sent before the upload must not arrive after it and restore the old text.
        await queryClient.cancelQueries({ queryKey: ideKeys.session(id) });
        const saved = await putFiles(id, sent, entry, pick(hashesOf(), Object.keys(sent)));
        queryClient.setQueryData(ideKeys.session(id), saved);
        markMine(mine);
        setEdits((current) => withoutSent(current, sent));
        return true;
      } catch (failure) {
        if (failure instanceof ApiError && failure.code === "stale_base") {
          await queryClient.refetchQueries({ queryKey: ideKeys.session(id) });
        } else {
          setError(errorMessage(failure));
        }
        return false;
      } finally {
        setSaving(false);
      }
    },
    [queryClient, id, entry, hashesOf, setEdits, markMine],
  );
  return { send, saving, error };
}
