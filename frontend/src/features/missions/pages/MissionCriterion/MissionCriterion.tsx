import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { Criterion } from "../../api";
import { CriterionForm } from "../CriterionForm";
import type { Changes } from "./criterionDraft";

type Props = {
  criterion: Criterion;
  editable: boolean;
  working: boolean;
  onSave: (progress: Changes, onSaved: () => void) => void;
};

const levels = {
  not_started: "missions.notStarted",
  in_progress: "missions.inProgress",
  achieved: "missions.achieved",
} as const;

export function MissionCriterion({ criterion, editable, working, onSave }: Props) {
  const title = useId();
  return (
    <section aria-labelledby={title} className="rounded-md border border-border p-4">
      <h3 id={title} className="font-semibold">
        {criterion.text}
      </h3>
      <p>
        {t(criterion.required ? "missions.required" : "missions.optional")} ·{" "}
        {t(levels[criterion.level])}
      </p>
      {criterion.skills.length > 0 && <p>{criterion.skills.join(", ")}</p>}
      <p className="mt-2">{t("missions.measurement")}</p>
      {editable ? (
        <CriterionForm criterion={criterion} working={working} onSave={onSave} />
      ) : (
        criterion.note && <p className="mt-2 whitespace-pre-wrap break-words">{criterion.note}</p>
      )}
    </section>
  );
}
