import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { InlineError } from "@/shared/ui/states/InlineError";

/** Longueur minimale du sujet acceptée par le graphe `demo_debate` (côté serveur : `min_length=3`). */
const MIN_TOPIC_LENGTH = 3;

interface DemoTopicFormProps {
  pending: boolean;
  error: string | null;
  onSubmit: (topic: string) => void;
}

/** Formulaire de lancement de la démo : un sujet de débat. */
export function DemoTopicForm({ pending, error, onSubmit }: DemoTopicFormProps) {
  const [topic, setTopic] = useState("");
  const trimmed = topic.trim();
  const canSubmit = !pending && trimmed.length >= MIN_TOPIC_LENGTH;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSubmit) onSubmit(trimmed);
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
      <Button type="submit" disabled={!canSubmit} className="self-start">
        {pending ? t("demo.topic.starting") : t("demo.topic.submit")}
      </Button>
    </form>
  );
}
