import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { putProjectTabs, type TabsState } from "../projectApi";
import type { IdeSession } from "../types";

function tabsFor(session: IdeSession, saved?: TabsState | null): TabsState {
  const openPaths = (saved?.open_paths ?? Object.keys(session.files)).filter(
    (path) => path in session.files,
  );
  if (openPaths.length === 0) openPaths.push(session.entry);
  const active = saved?.active_path ?? session.entry;
  return { open_paths: openPaths, active_path: openPaths.includes(active) ? active : openPaths[0] };
}

export function useProjectTabs(session: IdeSession) {
  const [local, setLocal] = useState<TabsState | null>(null);
  const view = tabsFor(session, local ?? session.tabs);
  const persist = useMutation({
    scope: { id: `ide-project-${session.id}` },
    mutationFn: (next: TabsState) => putProjectTabs(session.id, next),
  });

  function remember(next: TabsState, source: IdeSession) {
    setLocal(next);
    if (source.tabs) persist.mutate(next);
  }

  function openFile(path: string, source = session) {
    if (!(path in source.files)) return;
    const base = source === session ? view : tabsFor(source, source.tabs);
    const openPaths = Array.from(new Set([...base.open_paths, path]));
    remember({ open_paths: openPaths, active_path: path }, source);
  }

  function closeFile(path: string) {
    const next = tabsFor(session, {
      open_paths: view.open_paths.filter((name) => name !== path),
      active_path: view.active_path,
    });
    remember(next, session);
  }

  return {
    paths: view.open_paths,
    file: view.active_path ?? session.entry,
    openFile,
    closeFile,
    follow: (updated: IdeSession) => setLocal(updated.tabs ?? null),
    error: persist.error,
  };
}
