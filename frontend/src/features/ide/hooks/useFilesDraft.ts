import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";
import { omit, type Files } from "./fileMaps";
import { useClaudeChanges } from "./useClaudeChanges";
import { AUTOSAVE_MS, useDraftSave } from "./useDraftSave";

export { AUTOSAVE_MS };

/**
 * Les fichiers tels qu'on les édite : ce que le serveur a, plus les retouches pas encore
 * envoyées. Enregistre tout seul après 1,5 s sans frappe ; `save` attend un envoi en cours et rend
 * vrai si tout est enregistré (l'exécution l'appelle avant de partir). `discard` jette les
 * retouches quand le serveur a changé le fichier (proposition acceptée).
 *
 * La séance est relue en direct : si Claude change un fichier sur le serveur, l'éditeur le charge
 * et le dit (`claude.notices`) ; si tu avais des retouches pas enregistrées sur ce fichier, elles
 * sont gardées, rien n'est envoyé pour lui, et tu choisis (`claude.conflicts`) : jamais de perte
 * silencieuse, dans un sens ou dans l'autre.
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
      // Tu écris dans un fichier que Claude vient de changer : tu pars de sa version, sans conflit.
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
