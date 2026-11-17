import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { GenerateDraft, Level } from "../viewTypes";

interface GenerateExerciseFormProps {
  pending: boolean;
  onGenerate: (draft: GenerateDraft) => void;
}

const LEVELS: readonly Level[] = ["beginner", "intermediate", "advanced"];

/** Faire écrire un exercice par les agents : un sujet et un niveau. */
export function GenerateExerciseForm({ pending, onGenerate }: GenerateExerciseFormProps) {
  const topicId = useId();
  const levelId = useId();
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState<Level>("beginner");
  const ready = topic.trim() !== "";
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (ready && !pending) onGenerate({ topic: topic.trim(), level });
      }}
    >
      <h3 className="font-medium">{t("ide.form.generate")}</h3>
      <label htmlFor={topicId} className="text-sm font-medium">
        {t("ide.form.topic")}
      </label>
      <input
        id={topicId}
        value={topic}
        maxLength={300}
        aria-describedby={`${topicId}-hint`}
        onChange={(event) => setTopic(event.target.value)}
        className={fieldClass}
      />
      <p id={`${topicId}-hint`} className="text-xs text-muted-foreground">
        {t("ide.form.topicHint")}
      </p>
      <label htmlFor={levelId} className="text-sm font-medium">
        {t("ide.form.level")}
      </label>
      <select
        id={levelId}
        value={level}
        onChange={(event) => setLevel(event.target.value as Level)}
        className={fieldClass}
      >
        {LEVELS.map((value) => (
          <option key={value} value={value}>
            {t(`ide.form.levels.${value}`)}
          </option>
        ))}
      </select>
      <Button type="submit" className="self-start" disabled={!ready} aria-disabled={pending}>
        {t("ide.form.generateAction")}
      </Button>
    </form>
  );
}
