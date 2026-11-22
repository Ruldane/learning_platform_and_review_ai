import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { ComparisonBody } from "./ComparisonBody";
import type { Metrics, Reference } from "./viewTypes";

const at = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium" });

interface Props {
  kind: "ide" | "quiz";
  attempts: Reference[];
  selected: Reference | undefined;
  onSelect: (id: string) => void;
  current: Metrics | null;
  ongoing?: boolean;
}

export function GhostComparison({ kind, attempts, selected, onSelect, current, ongoing }: Props) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="space-y-2 rounded-xl border bg-card p-3 text-sm">
      <h2 id={id} className="font-semibold">
        {t("ghost.title")}
      </h2>
      {attempts.length === 0 ? (
        <p>{t("ghost.empty")}</p>
      ) : (
        <div className="flex flex-wrap items-baseline gap-2">
          <label htmlFor={`${id}-reference`}>{t("ghost.choose")}</label>
          <select
            id={`${id}-reference`}
            className="rounded-md border bg-background p-2 focus-visible:outline-2"
            value={selected?.id ?? ""}
            onChange={(event) => onSelect(event.target.value)}
          >
            <option value="">{t("ghost.choosePrompt")}</option>
            {attempts.map((attempt) => (
              <option key={attempt.id} value={attempt.id}>
                {at.format(new Date(attempt.at))}
              </option>
            ))}
          </select>
        </div>
      )}
      {selected && (
        <ComparisonBody kind={kind} selected={selected} current={current} ongoing={ongoing} />
      )}
    </section>
  );
}
