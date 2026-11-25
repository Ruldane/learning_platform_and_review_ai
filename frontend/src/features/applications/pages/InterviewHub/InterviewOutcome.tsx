import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { SalaryScenario } from "../../components/SalaryScenario";
import type { InterviewView } from "../../types";
import { InterviewResult } from "./InterviewResult";

interface InterviewOutcomeProps {
  interview: InterviewView;
  /** Back label: « Commencer un autre entretien » if followed, « Retour aux réglages » if past. */
  closeLabel: string;
  onClose: () => void;
}

/**
 * A finished (or past) interview: the heading gets focus on arrival, then the result by state:
 * debrief, answers without a debrief, stop before any answer, or session failure.
 */
export function InterviewOutcome({ interview, closeLabel, onClose }: InterviewOutcomeProps) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => title.current?.focus(), []);
  return (
    <section className="flex flex-col gap-4">
      <h2 ref={title} tabIndex={-1} className="text-xl font-semibold outline-none">
        {t("applications.debrief.title")}
      </h2>
      {interview.salary ? <SalaryScenario data={interview.salary} /> : null}
      <InterviewResult interview={interview} />
      <div>
        <Button type="button" variant="outline" onClick={onClose}>
          {closeLabel}
        </Button>
      </div>
    </section>
  );
}
