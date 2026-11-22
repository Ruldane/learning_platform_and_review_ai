import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { NamedOption, RubricView } from "../viewTypes";

interface Props {
  sources: NamedOption[];
  rubrics: RubricView[];
  busy: boolean;
  onSubmit: (first: string, second: string, rubric: string) => void;
}

function options(items: NamedOption[], except?: string) {
  return items.map((item) => (
    <option key={item.id} value={item.id} disabled={item.id === except}>
      {item.title}
    </option>
  ));
}

export function BlindForm({ sources, rubrics, busy, onSubmit }: Props) {
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [grid, setGrid] = useState("");
  const firstField = useId();
  const secondField = useId();
  const rubricField = useId();
  const selected = rubrics.find((row) => row.id === grid);
  const complete = Boolean(first && second && first !== second && selected);
  return (
    <form
      className="grid gap-3 rounded-xl border bg-card p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (complete) onSubmit(first, second, grid);
      }}
    >
      <label htmlFor={firstField}>{t("blindAssessment.first")}</label>
      <select id={firstField} className={fieldClass} value={first} onChange={(event) => setFirst(event.target.value)}>
        <option value="">{t("blindAssessment.chooseVersion")}</option>
        {options(sources, second)}
      </select>
      <label htmlFor={secondField}>{t("blindAssessment.second")}</label>
      <select id={secondField} className={fieldClass} value={second} onChange={(event) => setSecond(event.target.value)}>
        <option value="">{t("blindAssessment.chooseVersion")}</option>
        {options(sources, first)}
      </select>
      <label htmlFor={rubricField}>{t("blindAssessment.rubric")}</label>
      <select id={rubricField} className={fieldClass} value={grid} onChange={(event) => setGrid(event.target.value)}>
        <option value="">{t("blindAssessment.chooseRubric")}</option>
        {options(rubrics)}
      </select>
      {selected ? (
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {selected.criteria.map((criterion) => (
            <li key={criterion.label}><strong>{criterion.label}</strong> · {criterion.instructions}</li>
          ))}
        </ul>
      ) : null}
      <Button type="submit" className="justify-self-start" disabled={busy || !complete}>
        {t("blindAssessment.save")}
      </Button>
    </form>
  );
}
