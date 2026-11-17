import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchTokens } from "../api";
import type { TokenView } from "../components/viewTypes";
import { mcpKeys } from "../queryKeys";
import { toTokenView } from "../toView";

/** Les jetons, sans leur valeur (`GET /mcp/tokens`). */
export function useTokens() {
  const query = useQuery({
    queryKey: mcpKeys.tokens,
    queryFn: ({ signal }) => fetchTokens(signal),
  });
  const tokens = useMemo<TokenView[]>(() => {
    const now = new Date();
    return query.data?.map((token) => toTokenView(token, now)) ?? [];
  }, [query.data]);
  return { query, tokens };
}
