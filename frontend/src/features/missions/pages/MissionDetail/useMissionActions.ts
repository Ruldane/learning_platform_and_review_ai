import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveCriterion, submitMission, type Mission, type Progress } from "../../api";
import { missionsKey, saveMission } from "../../cache";

export function useMissionActions(mission: Mission, restoreFocus: () => void) {
  const cache = useQueryClient();
  const refresh = () => void cache.invalidateQueries({ queryKey: missionsKey, exact: true });
  const update = useMutation({
    mutationFn: ({ index, progress }: { index: number; progress: Progress }) =>
      saveCriterion(mission.id, index, progress),
    onSuccess: (value) => saveMission(cache, value),
    onError: refresh,
  });
  const finish = useMutation({
    mutationFn: (artifact: string) => submitMission(mission.id, mission.revision, artifact),
    onSuccess: (value) => {
      restoreFocus();
      saveMission(cache, value);
    },
    onError: refresh,
  });
  return { update, finish, working: update.isPending || finish.isPending };
}
