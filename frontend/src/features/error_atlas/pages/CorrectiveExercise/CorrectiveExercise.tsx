import { t } from "@/shared/i18n/t";
import type { Hypothesis } from "../../api";
import { EvidenceCard } from "../EvidenceCard";

export function CorrectiveExercise({
  exercise,
}: {
  exercise: NonNullable<Hypothesis["exercise"]>;
}) {
  return (
    <section className="flex flex-col gap-2 rounded border border-border p-3">
      <h4 className="font-semibold">{t("errorAtlas.exercise")}</h4>
      <ol className="list-decimal pl-5">
        {exercise.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <details>
        <summary>{t("errorAtlas.exerciseSources")}</summary>
        <ul className="flex flex-col gap-2 pt-2">
          {exercise.evidence.map((value) => (
            <li key={JSON.stringify(value.reference)}>
              <EvidenceCard value={value} />
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
