import { useEffect, useRef } from "react";
import type { RunStarted } from "../types";

/**
 * Montre dans la sortie l'exécution que Claude (MCP) vient de lancer : la plus récente de la liste
 * relue en direct, d'origine `mcp`, qu'on n'a pas déjà vue. À la première lecture, les exécutions
 * déjà finies sont connues (on n'affiche pas un vieux résultat à l'ouverture) ; une exécution encore
 * en cours, elle, est suivie. Ne touche jamais au focus ni au professeur.
 */
export function useClaudeRuns(
  runs: RunStarted[] | undefined,
  currentId: string | null,
  watch: (run: { id: string; kind: RunStarted["kind"]; origin: "mcp" }) => void,
) {
  const known = useRef<Set<string> | null>(null);
  useEffect(() => {
    if (!runs) return;
    if (known.current === null) {
      known.current = new Set(runs.filter((run) => run.status !== "running").map((run) => run.id));
    }
    const newest = runs[0];
    if (!newest || newest.origin !== "mcp") return;
    if (known.current.has(newest.id) || newest.id === currentId) return;
    known.current.add(newest.id);
    watch({ id: newest.id, kind: newest.kind, origin: "mcp" });
  }, [runs, currentId, watch]);
}
