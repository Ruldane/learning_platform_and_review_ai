import { useId, useState, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { GenerateDraft, Level } from "../viewTypes";
import { GenerateLevelField } from "./GenerateLevelField";

interface GenerateExerciseFormProps {
  pending: boolean;
  launchMenu?: ReactNode;
  onGenerate: (draft: GenerateDraft) => void;
}

/** Have the agents write an exercise: a topic and a level. */
export function GenerateExerciseForm({
  pending,
  onGenerate,
  launchMenu,
}: GenerateExerciseFormProps) {
  const topicId = useId();
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
      <GenerateLevelField level={level} onChange={setLevel} />
      {launchMenu}
      <Button type="submit" className="self-start" disabled={!ready} aria-disabled={pending}>
        {t("ide.form.generateAction")}
      </Button>
    </form>
  );
}
