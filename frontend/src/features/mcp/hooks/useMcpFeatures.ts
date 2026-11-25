import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchFeatures } from "../api";
import type { FeatureOption } from "../components/viewTypes";
import { mcpKeys } from "../queryKeys";
import { toFeatureOption } from "../toView";

/** The features that declare MCP tools (`GET /mcp/features`), to tick for a token. */
export function useMcpFeatures() {
  const query = useQuery({
    queryKey: mcpKeys.features,
    queryFn: ({ signal }) => fetchFeatures(signal),
  });
  const options = useMemo<FeatureOption[]>(
    () => query.data?.map(toFeatureOption) ?? [],
    [query.data],
  );
  return { query, options };
}
