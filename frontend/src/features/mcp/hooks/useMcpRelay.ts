import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { mcpKeys } from "../queryKeys";
import { fetchRelayStatus, pairRelay, revokeRelay } from "../relayApi";

export function useMcpRelay() {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: mcpKeys.relay,
    queryFn: ({ signal }) => fetchRelayStatus(signal),
    refetchInterval: (query) => (query.state.data?.state === "pending" ? 2_000 : false),
  });
  const action = useMutation({
    mutationFn: (kind: "pair" | "revoke") => (kind === "pair" ? pairRelay() : revokeRelay()),
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: mcpKeys.relay }),
        queryClient.invalidateQueries({ queryKey: mcpKeys.tokens }),
      ]);
    },
  });
  return { status, action };
}
