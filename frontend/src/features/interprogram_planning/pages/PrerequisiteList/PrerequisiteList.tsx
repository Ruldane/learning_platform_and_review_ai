import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Week } from "../../api";

const states = {
  completed: "interprogramPlanning.completed",
  planned: "interprogramPlanning.planned",
  pending: "interprogramPlanning.pending",
  unmatched: "interprogramPlanning.unmatched",
} as const;

export function PrerequisiteList({ items }: { items: Week["prerequisites"] }) {
  if (!items.length) return null;
  return (
    <div>
      <h4 className="font-semibold">{t("interprogramPlanning.prerequisites")}</h4>
      <ul className="flex list-inside list-disc flex-col gap-1">
        {items.map(({ module, label, status, references }) => (
          <li key={`${module.id}:${label}`}>
            {t("interprogramPlanning.prerequisite", { module: module.title, label })} ·{" "}
            {t(states[status])}
            {references.length > 0 && (
              <ul
                className="flex flex-wrap gap-2 pl-4"
                aria-label={t("interprogramPlanning.references")}
              >
                {references.map((ref) => (
                  <li key={ref.id}>
                    <Link
                      className="underline"
                      to={`/learn/programs/${encodeURIComponent(ref.program_id)}`}
                    >
                      {ref.title}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
