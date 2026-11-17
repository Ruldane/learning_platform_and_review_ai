import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchFeatures } from "../api";
import type { FeatureOption } from "../components/viewTypes";
import { mcpKeys } from "../queryKeys";
import { toFeatureOption } from "../toView";

/** Les features qui déclarent des outils MCP (`GET /mcp/features`), à cocher pour un jeton. */
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
