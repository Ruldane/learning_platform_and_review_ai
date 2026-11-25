import { useState } from "react";
import type { NotebookCell } from "../notebookApi";

interface NotebookDraft {
  cells: NotebookCell[];
  version: number;
}

/** Session drafts, indexed by path and anchored to the version of the first edit. */
export function useNotebookDrafts() {
  const [drafts, setDrafts] = useState<ReadonlyMap<string, NotebookDraft>>(() => new Map());
  const edit = (path: string, cells: NotebookCell[], version: number) => {
    setDrafts((current) =>
      new Map(current).set(path, { cells, version: current.get(path)?.version ?? version }),
    );
  };
  const clear = (path: string, saved: NotebookDraft) => {
    setDrafts((current) => {
      if (current.get(path) !== saved) return current;
      const next = new Map(current);
      next.delete(path);
      return next;
    });
  };
  return { drafts, edit, clear };
}

export type NotebookDrafts = ReturnType<typeof useNotebookDrafts>;
