import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { DesignReview } from "../../systemDesignApi";

const axes = ["architecture", "reliability", "scale", "tradeoffs"] as const;

export function SystemDesignReview({ review, proof }: { review: DesignReview; proof: boolean }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <section className="flex max-w-3xl flex-col gap-3">
      <h2 ref={heading} tabIndex={-1} className="text-xl font-semibold">
        {t("systemDesign.review")}
      </h2>
      <p>{review.summary}</p>
      <dl className="grid gap-2 sm:grid-cols-2">
        {axes.map((axis) => (
          <div key={axis} className="rounded-md border border-border p-3">
            <dt className="font-semibold">{t(`systemDesign.criteria.${axis}`)}</dt>
            <dd>
              <p>{t("systemDesign.score", { score: review.criteria[axis].score })}</p>
              <p>{review.criteria[axis].feedback}</p>
            </dd>
          </div>
        ))}
      </dl>
      {proof && <p>{t("systemDesign.proof")}</p>}
    </section>
  );
}
