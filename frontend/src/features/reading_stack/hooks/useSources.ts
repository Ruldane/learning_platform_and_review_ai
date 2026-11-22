import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addReadingSource, listReadingSources, removeReadingSource, setSourceActive } from "../api";
import { readingKeys } from "../queryKeys";

export function useSources(open: boolean, onRemove: () => void) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: readingKeys.sources,
    enabled: open,
    queryFn: ({ signal }) => listReadingSources(signal),
  });
  const refresh = () => void client.invalidateQueries({ queryKey: readingKeys.sources });
  const add = useMutation({ mutationFn: addReadingSource, onSuccess: refresh });
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setSourceActive(id, active),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: removeReadingSource,
    onSuccess: () => {
      onRemove();
      refresh();
    },
  });
  return {
    query,
    add,
    toggle,
    remove,
    error: query.error ?? add.error ?? toggle.error ?? remove.error,
    busy: add.isPending || toggle.isPending || remove.isPending,
  };
}
