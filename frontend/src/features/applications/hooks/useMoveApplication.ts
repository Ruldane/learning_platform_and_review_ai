import { useMutation, useQueryClient } from "@tanstack/react-query";
import { postEvent } from "../api";
import { applicationsErrorMessage } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { ApplicationOut, StatusView } from "../types";

interface Move {
  id: string;
  status: StatusView;
}

const withStatus = (rows: ApplicationOut[] | undefined, { id, status }: Move) =>
  rows?.map((row) => (row.id === id ? { ...row, status } : row));

/**
 * Moves a record to another column (`POST /applications/{id}/events`, a status change
 * dated today). The board follows at once; if the server refuses, the record
 * goes back to its column and `error` says so. Dates, reminders and indicators are re-read.
 */
export function useMoveApplication() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, status }: Move) => postEvent(id, { kind: "status", status }),
    onMutate: async (move) => {
      await client.cancelQueries({ queryKey: applicationsKeys.list });
      const previous = client.getQueryData<ApplicationOut[]>(applicationsKeys.list);
      client.setQueryData<ApplicationOut[]>(applicationsKeys.list, (rows) =>
        withStatus(rows, move),
      );
      return { previous };
    },
    onError: (_error, _move, context) =>
      client.setQueryData(applicationsKeys.list, context?.previous),
    onSettled: () => client.invalidateQueries({ queryKey: applicationsKeys.all }),
  });
  const { mutate, reset } = mutation;
  return {
    move: (id: string, status: StatusView) => {
      reset();
      mutate({ id, status });
    },
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
  };
}
