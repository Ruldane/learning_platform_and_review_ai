import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState, type Dispatch, type SetStateAction } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { putFiles } from "../api";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";
import { pick, type Files } from "./fileMaps";

/** Ce qui reste à envoyer une fois `sent` parti : une retouche faite pendant l'envoi est gardée. */
const withoutSent = (edits: Files, sent: Files): Files =>
  Object.fromEntries(Object.entries(edits).filter(([name, text]) => sent[name] !== text));

/**
 * L'envoi des fichiers au serveur, avec l'empreinte de la version sur laquelle chacun a été édité
 * (`hashesOf`, lue au moment de l'envoi) : si Claude a écrit depuis (409 `stale_base`), rien n'est
 * enregistré, la séance est relue, et le choix (garder la tienne, prendre la sienne) apparaît pour
 * les fichiers concernés.
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
        // Une relecture partie avant l.envoi ne doit pas arriver après et remettre l'ancien texte.
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
