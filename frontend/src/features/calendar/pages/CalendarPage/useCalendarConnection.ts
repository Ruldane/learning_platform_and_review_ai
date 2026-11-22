import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { connect, disconnect, getConnection } from "../../api";

const connectionKey = ["calendar", "connection"] as const;

export function useCalendarConnection() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: connectionKey,
    queryFn: ({ signal }) => getConnection(signal),
  });
  const login = useMutation({
    mutationFn: connect,
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
  });
  const logout = useMutation({
    mutationFn: disconnect,
    onSuccess: (status) => {
      client.setQueryData(connectionKey, status);
    },
    onError: () => client.invalidateQueries({ queryKey: connectionKey }),
  });
  return {
    query,
    status: query.data?.status,
    error: login.error ?? logout.error,
    pending: login.isPending || logout.isPending,
    connect: () => {
      logout.reset();
      login.mutate();
    },
    disconnect: () => {
      login.reset();
      logout.mutate();
    },
  };
}
