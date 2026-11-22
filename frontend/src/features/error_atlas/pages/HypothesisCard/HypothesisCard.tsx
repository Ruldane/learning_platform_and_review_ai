import { useId, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Hypothesis } from "../../api";
import { confidenceLabels } from "../../labels";
import { CorrectiveExercise } from "../CorrectiveExercise";
import { EvidenceCard } from "../EvidenceCard";
import { useCorrectiveExercise } from "./useCorrectiveExercise";

export function HypothesisCard({ group }: { group: Hypothesis }) {
  const heading = useRef<HTMLHeadingElement>(null);
  const title = useId();
  const choose = useCorrectiveExercise(group.id, () => heading.current?.focus());
  const count = group.observations.length;
  return (
    <section
      aria-labelledby={title}
      className="rounded border border-border p-4 flex flex-col gap-3"
    >
      <h3 ref={heading} id={title} tabIndex={-1} className="font-semibold">
        {group.label}
      </h3>
      <p>
        {count === 1 ? t("errorAtlas.observationOne") : t("errorAtlas.observations", { count })}
        {" · "}
        {t("errorAtlas.confidence")} — {t(confidenceLabels[group.confidence])}
      </p>
      <ul className="flex flex-col gap-3">
        {group.observations.map((item) => (
          <li key={item.id}>
            <EvidenceCard value={item.evidence} />
            <p className="pl-3 text-sm">
              {t("errorAtlas.confidence")} — {t(confidenceLabels[item.confidence])}
            </p>
          </li>
        ))}
      </ul>
      {group.exercise ? (
        <CorrectiveExercise exercise={group.exercise} />
      ) : (
        <Button
          type="button"
          className="self-start"
          aria-disabled={choose.isPending}
          onClick={() => {
            if (!choose.isPending) choose.mutate();
          }}
        >
          {t("errorAtlas.chooseExercise")}
        </Button>
      )}
      {choose.isError && <p role="alert">{errorMessage(choose.error)}</p>}
    </section>
  );
}
