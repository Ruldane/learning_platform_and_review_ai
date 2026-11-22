import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { startMission, type Posting } from "../../api";
import { missionsKey, saveMission } from "../../cache";
import { RequirementChoices } from "../RequirementChoices";

export function MissionRequirements({
  offer,
  onCreated,
}: {
  offer: Posting;
  onCreated: () => void;
}) {
  const [chosen, setChosen] = useState<number[]>([]);
  const cache = useQueryClient();
  const start = useMutation({
    mutationFn: () => startMission(offer.id, chosen),
    onSuccess: (mission) => {
      onCreated();
      saveMission(cache, mission);
    },
    onError: () => void cache.invalidateQueries({ queryKey: missionsKey, exact: true }),
  });
  const requirements = offer.status === "ready" ? (offer.analysis?.requirements ?? []) : [];
  return (
    <section>
      <h2 className="text-lg font-semibold">{offer.title ?? t("missions.untitled")}</h2>
      {requirements.length === 0 ? (
        <p>{t("missions.noRequirements")}</p>
      ) : (
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (chosen.length && !start.isPending) start.mutate();
          }}
        >
          <RequirementChoices
            labels={requirements.map(({ text }) => text)}
            chosen={chosen}
            disabled={start.isPending}
            onToggle={(index, selected) =>
              setChosen((current) =>
                selected ? [...current, index] : current.filter((entry) => entry !== index),
              )
            }
          />
          {start.isError && <p role="alert">{errorMessage(start.error)}</p>}
          <Button type="submit" className="self-start" disabled={!chosen.length || start.isPending}>
            {t("missions.start")}
          </Button>
        </form>
      )}
    </section>
  );
}
