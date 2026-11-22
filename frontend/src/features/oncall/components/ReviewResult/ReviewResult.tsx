import { t } from "@/shared/i18n/t";

const criteria = ["diagnosis", "evidence", "correction", "prevention"] as const;

interface ReviewResultProps {
  scores: Record<(typeof criteria)[number], number>;
  feedback: string;
  proof: boolean;
}

export function ReviewResult({ scores, feedback, proof }: ReviewResultProps) {
  return (
    <section className="flex flex-col gap-3" aria-labelledby="oncall-review">
      <h2 id="oncall-review" className="text-xl font-semibold">
        {t("oncall.review")}
      </h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {criteria.map((criterion) => (
          <div key={criterion}>
            <dt>{t(`oncall.criteria.${criterion}`)}</dt>
            <dd className="font-semibold">{t("oncall.outOfFive", { score: scores[criterion] })}</dd>
          </div>
        ))}
      </dl>
      <p className="whitespace-pre-wrap">{feedback}</p>
      {proof && (
        <p role="status" className="font-semibold">
          {t("oncall.proof")}
        </p>
      )}
    </section>
  );
}
