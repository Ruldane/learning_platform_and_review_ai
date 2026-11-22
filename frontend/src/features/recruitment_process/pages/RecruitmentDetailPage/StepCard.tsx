import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { Recruitment, Step } from "../../api";

interface Props {
  step: Step;
  rubric: Recruitment["rubric"];
  active: boolean;
  pending: boolean;
  retry: boolean;
  onAnswer: (answer: string) => void;
}

export function StepCard({ step, rubric, active, pending, retry, onAnswer }: Props) {
  const [answer, change] = useState(step.answer ?? "");
  const id = useId();
  return (
    <article className="grid gap-3 rounded-xl border bg-card p-4">
      <h2 className="font-semibold">{t(`recruitmentProcess.step.${step.kind}`)}</h2>
      {active || step.grade ? <p className="whitespace-pre-wrap">{step.prompt}</p> : null}
      {active && !pending ? (
        <form className="grid gap-3" onSubmit={(event) => {
          event.preventDefault();
          if (answer.trim()) onAnswer(answer);
        }}>
          <label htmlFor={id}>{t("recruitmentProcess.response")}</label>
          <textarea id={id} className={fieldClass} rows={4} maxLength={8000} value={answer} onChange={(event) => change(event.target.value)} required />
          <Button type="submit" disabled={!answer.trim()} className="justify-self-start">
            {t(retry ? "recruitmentProcess.retry" : "recruitmentProcess.send")}
          </Button>
        </form>
      ) : null}
      {step.grade ? (
        <div className="grid gap-2">
          <h3 className="font-medium">{t("recruitmentProcess.grade")}</h3>
          <p className="whitespace-pre-wrap">{step.grade.feedback}</p>
          <ul className="list-disc pl-5">
            {rubric.map((item, index) => {
              const mark = step.grade?.marks[index];
              return <li key={item.label}>{item.label} {mark === undefined ? null : t("recruitmentProcess.score", { value: mark })}</li>;
            })}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
