import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { prepareReturn, startReturn, studyReturnKey } from "../../api";
import { trainingUrl } from "../../dates";

export function useReturnBlock() {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const reload = () => cache.invalidateQueries({ queryKey: studyReturnKey });
  const prepare = useMutation({ mutationFn: prepareReturn, onSuccess: reload });
  const start = useMutation({
    mutationFn: startReturn,
    onSuccess: (value) => {
      cache.setQueryData(studyReturnKey, value);
      if (value.plan?.training_id) void navigate(trainingUrl(value.plan.training_id));
      return reload();
    },
  });
  return { prepare, start, isWorking: prepare.isPending || start.isPending };
}
