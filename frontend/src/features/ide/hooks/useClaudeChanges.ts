import { useCallback, useState } from "react";
import { pick, type Files } from "./fileMaps";

/**
 * What Claude (via the MCP) changed in the files while the page is open. `server`
 * is the session re-read live, `edits` your unsaved edits. A file is
 * « changé par Claude » when the server no longer has the version you acknowledged (`seen`) nor
 * the one you saved yourself (`mine`). Then:
 * - without edits of yours: the editor already shows the new version, and says so (`notices`);
 * - with edits: yours stay on screen, nothing is sent for that file, and the
 *   conflict (`conflicts`, Claude's version per file) waits for your choice.
 * Everything is computed at render from these two marks: no effect, no message that
 * lingers; typing in a file you had no edits in acknowledges the server's version.
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
  /** Acknowledges the server's version (« Compris », « Garder la mienne », typing). */
  const acknowledge = useCallback(
    (names: string[]) => setSeen((current) => ({ ...current, ...pick(server, names) })),
    [server],
  );
  /** These texts come from you (save, accepted proposal): never Claude's. */
  const markMine = useCallback(
    (files: Files) => setMine((current) => ({ ...current, ...files })),
    [],
  );
  return { conflicts, notices, acknowledge, markMine };
}
