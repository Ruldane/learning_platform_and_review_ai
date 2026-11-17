import { useCallback, useState } from "react";
import { pick, type Files } from "./fileMaps";

/**
 * Ce que Claude (par le MCP) a changé dans les fichiers pendant que la page est ouverte. `server`
 * est la séance relue en direct, `edits` tes retouches pas encore enregistrées. Un fichier est
 * « changé par Claude » quand le serveur n'a plus la version que tu avais reconnue (`seen`) ni
 * celle que tu as toi-même enregistrée (`mine`). Alors :
 * - sans retouche de ta part : l'éditeur montre déjà la nouvelle version, on le dit (`notices`) ;
 * - avec des retouches : les tiennes restent à l'écran, rien n'est envoyé pour ce fichier, et le
 *   conflit (`conflicts`, la version de Claude par fichier) attend ton choix.
 * Tout est calculé à l'affichage à partir de ces deux repères : aucun effet, aucun message qui
 * traîne ; taper dans un fichier dont tu n'avais pas de retouche reconnaît la version du serveur.
 */
export function useClaudeChanges(server: Files, edits: Files) {
  const [seen, setSeen] = useState<Files>(server);
  const [mine, setMine] = useState<Files>({});
  const changed = Object.keys(server).filter(
    (name) => server[name] !== seen[name] && server[name] !== mine[name],
  );
  const conflicting = changed.filter((name) => name in edits && edits[name] !== server[name]);
  const conflicts = pick(server, conflicting);
  const notices = changed.filter((name) => !(name in edits));
  /** Reconnaît la version du serveur pour ces fichiers (« Compris », « Garder la mienne », frappe). */
  const acknowledge = useCallback(
    (names: string[]) => setSeen((current) => ({ ...current, ...pick(server, names) })),
    [server],
  );
  /** Ces textes viennent de toi (enregistrement, proposition acceptée) : jamais ceux de Claude. */
  const markMine = useCallback(
    (files: Files) => setMine((current) => ({ ...current, ...files })),
    [],
  );
  return { conflicts, notices, acknowledge, markMine };
}
