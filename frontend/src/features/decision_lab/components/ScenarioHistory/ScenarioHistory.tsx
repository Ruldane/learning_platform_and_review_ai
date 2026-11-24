import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ScenarioLink } from "../viewTypes";

const day = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" });

interface Props {
  scenarios: ScenarioLink[];
  onOpen: (id: string) => void;
  busy: boolean;
}

export function ScenarioHistory({ scenarios, onOpen, busy }: Props) {
  return (
    <section className="flex flex-col gap-2" aria-labelledby="decision-history">
      <h2 id="decision-history" className="text-lg font-semibold">{t("decisionLab.history")}</h2>
      {scenarios.length === 0 ? <p>{t("decisionLab.empty")}</p> : (
        <ul className="space-y-2">
          {scenarios.map((scenario) => (
            <li key={scenario.id} className="flex flex-wrap items-center gap-2">
              <Button
                type="button" variant="outline" disabled={busy}
                className="h-auto min-h-9 max-w-full whitespace-normal break-all text-left"
                onClick={() => onOpen(scenario.id)}
              >
                <span className="sr-only">{t("decisionLab.open")} </span>
                {scenario.title}
              </Button>
              <time dateTime={scenario.createdAt} className="text-sm text-muted-foreground">
                {day.format(new Date(scenario.createdAt))}
              </time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
