import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { Mission } from "../../api";
import { MissionCriterion } from "../MissionCriterion";
import { MissionSubmission } from "../MissionSubmission";
import { useMissionActions } from "./useMissionActions";

const statuses = {
  active: "missions.active",
  expired: "missions.expired",
  completed: "missions.completed",
} as const;

export function MissionDetail({ mission }: { mission: Mission }) {
  const heading = useRef<HTMLHeadingElement>(null);
  const { update, finish, working } = useMissionActions(mission, () => heading.current?.focus());
  const deadline = new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(mission.deadline_at));
  return (
    <section className="flex flex-col gap-4">
      <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">
        {mission.posting_title ?? t("missions.untitled")}
      </h2>
      {mission.company && <p>{mission.company}</p>}
      <p>
        <strong>{t(statuses[mission.status])}</strong> ·{" "}
        {t("missions.deadline", { date: deadline })}
      </p>
      <p>{t("missions.project")}</p>
      {mission.criteria.map((criterion) => (
        <MissionCriterion
          key={criterion.index}
          criterion={criterion}
          editable={mission.status === "active"}
          working={working}
          onSave={(progress, onSaved) => {
            finish.reset();
            update.mutate(
              { index: criterion.index, progress: { revision: mission.revision, ...progress } },
              { onSuccess: onSaved },
            );
          }}
        />
      ))}
      {update.isSuccess && <p role="status">{t("missions.saved")}</p>}
      {update.isError && <p role="alert">{errorMessage(update.error)}</p>}
      <MissionSubmission
        mission={mission}
        working={working}
        error={finish.error}
        onSubmit={(artifact) => {
          update.reset();
          finish.mutate(artifact);
        }}
      />
    </section>
  );
}
