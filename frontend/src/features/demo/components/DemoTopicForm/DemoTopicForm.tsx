import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { InlineError } from "@/shared/ui/states/InlineError";

/** Minimum topic length accepted by the `demo_debate` graph (server side: `min_length=3`). */
const MIN_TOPIC_LENGTH = 3;

interface DemoTopicFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (topic: string, source?: RunSource) => void;
}

/** Demo launch form: a debate topic. */
export function DemoTopicForm({ pending, error, onSubmit }: DemoTopicFormProps) {
  const [topic, setTopic] = useState("");
  const launch = useLaunchSource();
  const trimmed = topic.trim();
  const canSubmit = !pending && trimmed.length >= MIN_TOPIC_LENGTH;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSubmit) onSubmit(trimmed, launch.source);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("demo.topic.label")}
        <input
          type="text"
          value={topic}
          maxLength={200}
          placeholder={t("demo.topic.placeholder")}
          onChange={(event) => setTopic(event.target.value)}
          className={fieldClass}
        />
      </label>
      {error ? <InlineError message={error} /> : null}
      {launch.menu}
      <Button type="submit" disabled={!canSubmit} className="self-start">
        {pending ? t("demo.topic.starting") : t("demo.topic.submit")}
      </Button>
    </form>
  );
}
