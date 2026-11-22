import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Week } from "../../api";
import { PrerequisiteList } from "../PrerequisiteList";
import { WeekPlacements } from "../WeekPlacements";

const issues = {
  no_tasks: "interprogramPlanning.noTasks",
  weekly_budget: "interprogramPlanning.weeklyBudget",
  program_budget: "interprogramPlanning.programBudget",
  prerequisites: "interprogramPlanning.prerequisitesIssue",
  capacity: "interprogramPlanning.capacityIssue",
} as const;

export function WeekDetails({ week }: { week: Week }) {
  return (
    <>
      <div>
        <h4 className="font-semibold">{t("interprogramPlanning.programs")}</h4>
        <ul className="list-inside list-disc">
          {week.programs.map(({ id, title }) => (
            <li key={id}>
              <Link className="underline" to={`/apprendre/programme/${encodeURIComponent(id)}`}>
                {title}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      {week.issues.length > 0 && (
        <ul className="list-inside list-disc">
          {week.issues.map((issue) => (
            <li key={issue}>{t(issues[issue])}</li>
          ))}
        </ul>
      )}
      <WeekPlacements tasks={week.placements} />
      <PrerequisiteList items={week.prerequisites} />
      {week.unplaced.length > 0 && (
        <div>
          <h4 className="font-semibold">{t("interprogramPlanning.unplaced")}</h4>
          <ul className="list-inside list-disc">
            {week.unplaced.map((task) => (
              <li key={task.task_id}>{task.title}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
