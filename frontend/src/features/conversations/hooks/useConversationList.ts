import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import type { ConversationListAction } from "../components/ConversationList";
import {
  clearThread,
  deleteThread,
  deleteThreads,
  listThreads,
  renameThread,
  type ConversationSpace,
  type ConversationSummary,
} from "../threadsApi";

import { listKey, useConversationSearch } from "./useConversationSearch";

export { listKey } from "./useConversationSearch";
export const threadKey = (scope: ConversationSpace, id?: string) =>
  ["conversations", scope, "thread", id ?? "open"] as const;

async function apply(scope: ConversationSpace, action: ConversationListAction) {
  switch (action.kind) {
    case "rename":
      return renameThread(scope, action.id, action.title);
    case "clear":
      return clearThread(scope, action.id);
    case "delete":
      return deleteThread(scope, action.id);
    case "wipe":
      return deleteThreads(scope);
  }
}

function updateList(
  entries: ConversationSummary[] | undefined,
  action: ConversationListAction,
  updated: ConversationSummary | void,
) {
  if (updated) return entries?.map((entry) => (entry.id === updated.id ? updated : entry));
  if (action.kind === "delete") return entries?.filter((entry) => entry.id !== action.id);
  if (action.kind === "wipe") return [];
  return entries;
}

export function useConversationList(
  scope: ConversationSpace,
  onChanged: (action: ConversationListAction) => void,
) {
  const client = useQueryClient();
  const newRef = useRef<HTMLButtonElement>(null);
  const key = listKey(scope);
  const list = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => listThreads(scope, undefined, signal),
  });
  const search = useConversationSearch(scope);
  const refresh = () => void client.invalidateQueries({ queryKey: key });
  const change = useMutation({
    mutationFn: (action: ConversationListAction) => apply(scope, action),
    onSuccess: (updated, action) => {
      client.setQueryData<ConversationSummary[]>(key, (entries) =>
        updateList(entries, action, updated),
      );
      onChanged(action);
      refresh();
      if (action.kind !== "rename") {
        void client.invalidateQueries({ queryKey: ["conversations", scope, "thread"] });
      }
    },
  });
  const removed =
    change.isSuccess && (change.variables.kind === "delete" || change.variables.kind === "wipe");
  useEffect(() => {
    if (removed) newRef.current?.focus();
  }, [removed, change.submittedAt]);
  const error = change.error ?? list.error ?? search.error;
  return {
    refresh,
    listPending: list.isPending,
    sidebar: {
      newRef,
      entries: list.data ?? [],
      visibleEntries: search.matches ?? list.data ?? [],
      search: search.search,
      onSearch: search.onSearch,
      pending: list.isPending || search.pending,
      busy: change.isPending,
      error: error ? errorMessage(error) : undefined,
      onAction: change.mutate,
    },
  };
}
