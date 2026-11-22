import { useMutation, useQueryClient } from "@tanstack/react-query";
import { setReminder, studyReturnKey } from "../../api";

export function useReminder(saved: () => void) {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: setReminder,
    onSuccess: async (value) => {
      saved();
      cache.setQueryData(studyReturnKey, value);
      await cache.invalidateQueries({ queryKey: studyReturnKey });
    },
  });
}
