import { useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  fetchNotebook,
  fetchNotebookRun,
  runNotebookCell,
  saveNotebook,
  type NotebookCell,
} from "../notebookApi";
import { ideKeys } from "../queryKeys";
import type { NotebookDrafts } from "./useNotebookDrafts";
import { useRunPolling } from "./useRunPolling";

type Operation = { cellId: string; includePrevious: boolean } | null;

export function useNotebook(sessionId: string, path: string, drafts: NotebookDrafts) {
  const cache = useQueryClient();
  const key = ideKeys.notebook(sessionId, path);
  const mutationKey = [...key, "action"];
  const pending = useIsMutating({ mutationKey, exact: true }) > 0;
  const draft = drafts.drafts.get(path);
  const [runId, setRun] = useState<string | null>(null);
  const query = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => fetchNotebook(sessionId, path, signal),
  });
  const cells = draft?.cells ?? query.data?.cells ?? [];
  const setDraft = (cells: NotebookCell[]) => {
    if (query.data) drafts.edit(path, cells, query.data.files_version);
  };
  const refresh = () => {
    void cache.invalidateQueries({ queryKey: key });
    void cache.invalidateQueries({ queryKey: ideKeys.session(sessionId) });
  };
  const activeId = runId ?? query.data?.active_run_id ?? null;
  const progress = useRunPolling(activeId, refresh, fetchNotebookRun);
  const action = useMutation({
    mutationKey,
    mutationFn: async (operation: Operation) => {
      if (!query.data) return;
      if (draft) {
        const values = draft.cells.map(({ id, kind, source }) => ({ id, kind, source }));
        const saved = await saveNotebook(sessionId, {
          path,
          version: draft.version,
          cells: values,
        });
        cache.setQueryData(key, saved);
        drafts.clear(path, draft);
        void cache.invalidateQueries({ queryKey: ideKeys.session(sessionId) });
      }
      if (operation) {
        const started = await runNotebookCell(sessionId, {
          path,
          cell_id: operation.cellId,
          include_previous: operation.includePrevious,
        });
        setRun(started.id);
      }
    },
  });
  return { query, cells, setDraft, dirty: draft !== undefined, progress, action, pending };
}
