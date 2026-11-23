import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listThreads, type ConversationSpace } from "../threadsApi";

export const listKey = (scope: ConversationSpace) => ["conversations", scope, "list"] as const;

export function useConversationSearch(scope: ConversationSpace) {
  const [search, onSearch] = useState("");
  const q = useDeferredValue(search.trim());
  const query = useQuery({
    queryKey: [...listKey(scope), q],
    queryFn: ({ signal }) => listThreads(scope, q, signal),
    enabled: q !== "",
  });
  return {
    search,
    onSearch,
    matches: q ? (query.data ?? []) : undefined,
    pending: q !== search.trim() || (q !== "" && query.isPending),
    error: q ? query.error : null,
  };
}
