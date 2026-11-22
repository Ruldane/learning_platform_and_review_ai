import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listPrograms, readBook, requestBook } from "./api";

export function usePrograms() {
  return useQuery({
    queryKey: ["book", "programs"],
    queryFn: ({ signal }) => listPrograms(signal),
  });
}

export function useBook(programId: string, pollMs: number) {
  const client = useQueryClient();
  const queryKey = ["book", "edition", programId] as const;
  const edition = useQuery({
    queryKey,
    queryFn: ({ signal }) => readBook(programId, signal),
    refetchInterval: ({ state }) => {
      if (state.data?.status === "not_requested") return false;
      return state.data?.status === "queued" ? pollMs : Math.max(pollMs, 10_000);
    },
    refetchIntervalInBackground: false,
  });
  const request = useMutation({
    mutationFn: requestBook,
    onSuccess: (data, id) => client.setQueryData(["book", "edition", id], data),
  });
  return { edition, request };
}
