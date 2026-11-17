import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ExerciseView } from "../../components/viewTypes";

interface ExerciseRowProps {
  exercise: ExerciseView;
  /** Une séance est en train de s'ouvrir : les boutons attendent. */
  busy: boolean;
  onOpen: (exercise: ExerciseView) => void;
}

const ACTION = { todo: "start", doing: "resume", passed: "review" } as const;

/** Un exercice : son état en texte, son énoncé à la demande, et le geste pour y travailler. */
export function ExerciseRow({ exercise, busy, onOpen }: ExerciseRowProps) {
  const headingId = useId();
  const action = t(`ide.home.${ACTION[exercise.state]}`);
  return (
    <article
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 id={headingId} className="font-medium">
          {exercise.title}
        </h3>
        <span className="rounded border border-border px-1.5 text-xs">
          {t(`ide.home.state.${exercise.state}`)}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {t(`ide.home.origin.${exercise.origin}`)}
        {exercise.topic ? ` · ${t("ide.home.topic", { topic: exercise.topic })}` : ""}
      </p>
      <details>
        <summary className="cursor-pointer text-sm">{t("ide.session.statement")}</summary>
        <p className="mt-1 max-w-prose text-sm whitespace-pre-wrap">{exercise.statement}</p>
      </details>
      <Button
        size="sm"
        className="self-start"
        aria-disabled={busy}
        aria-label={t("ide.home.startLabel", { action, title: exercise.title })}
        onClick={() => !busy && onOpen(exercise)}
      >
        {action}
      </Button>
    </article>
  );
}
