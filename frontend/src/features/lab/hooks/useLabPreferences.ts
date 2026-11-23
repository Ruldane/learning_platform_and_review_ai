import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchPreferences, savePreferences } from "../api";

const KEY = ["lab", "preferences"];

export function useLabPreferences(enabled = true) {
  const client = useQueryClient();
  const preferences = useQuery({
    queryKey: KEY,
    queryFn: ({ signal }) => fetchPreferences(signal),
    enabled,
    staleTime: 10_000,
  });
  const save = useMutation({
    mutationFn: savePreferences,
    scope: { id: "lab-preferences" },
    onMutate: () => client.cancelQueries({ queryKey: KEY }),
    onSuccess: (updated) => client.setQueryData(KEY, updated),
  });
  return { preferences, save };
}
