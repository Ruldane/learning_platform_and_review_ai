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
} from "../threadsApi";

export const listKey = (scope: ConversationSpace) => ["conversations", scope, "list"] as const;
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

export function useConversationList(
  scope: ConversationSpace,
  onChanged: (action: ConversationListAction) => void,
) {
  const client = useQueryClient();
  const newRef = useRef<HTMLButtonElement>(null);
  const key = listKey(scope);
  const list = useQuery({ queryKey: key, queryFn: ({ signal }) => listThreads(scope, signal) });
  const refresh = () => void client.invalidateQueries({ queryKey: key });
  const change = useMutation({
    mutationFn: (action: ConversationListAction) => apply(scope, action),
    onSuccess: (updated, action) => {
      if (updated) {
        client.setQueryData(
          key,
          list.data?.map((item) => (item.id === updated.id ? updated : item)),
        );
      }
      if (action.kind === "delete" || action.kind === "wipe") {
        client.setQueryData(
          key,
          action.kind === "wipe" ? [] : list.data?.filter((entry) => entry.id !== action.id),
        );
      }
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
  const error = change.error ?? list.error;
  return {
    refresh,
    sidebar: {
      newRef,
      entries: list.data ?? [],
      pending: list.isPending,
      busy: change.isPending,
      error: error ? errorMessage(error) : undefined,
      onAction: change.mutate,
    },
  };
}
