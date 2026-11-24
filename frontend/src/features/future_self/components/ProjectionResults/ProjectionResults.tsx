import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import type { ProjectionView } from "../viewTypes";
import { Chapters } from "./Chapters";
import { ScenarioCard } from "./ScenarioCard";
import { Today } from "./Today";

export function ProjectionResults({ projection }: { projection: ProjectionView }) {
  return (
    <div className="grid gap-6">
      <Today projection={projection} />
      {projection.notes.length > 0 ? (
        <div role="note" className="rounded-xl border bg-muted/40 p-4 text-sm">
          <ul className="grid gap-1">
            {projection.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <section aria-labelledby="projection-scenarios" className="grid gap-3">
        <h2 id="projection-scenarios" className="text-xl font-semibold">
          {t("futureSelf.scenarios")}
        </h2>
        <div className="grid gap-3 md:grid-cols-3">
          {projection.scenarios.map((scenario) => (
            <ScenarioCard key={scenario.id} scenario={scenario} target={projection.targetPercent} />
          ))}
        </div>
        <p className="text-sm text-muted-foreground">{t("futureSelf.criteria")}</p>
      </section>
      <Chapters items={projection.chapters} />
      {projection.programId ? (
        <Link
          to={`/learn/programs/${projection.programId}/replan`}
          className={buttonVariants({ variant: "outline", className: "justify-self-start" })}
        >
          {t("futureSelf.replan")}
        </Link>
      ) : null}
    </div>
  );
}
