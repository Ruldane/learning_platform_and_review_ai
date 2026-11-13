import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { StudyTimer, timerKey } from "../../components/StudyTimer";
import type { StudyRun } from "../../hooks/useStudyRun";
import type { StudySessionOut } from "../../types";
import { NewBlockStart } from "./NewBlockStart";
import { SessionTitle } from "./SessionTitle";

interface SessionHeaderProps {
  session: StudySessionOut;
  run: StudyRun;
  finishing: boolean;
  workMinutes: number;
  breakMinutes: number;
}

/**
 * En-tête de la session : la leçon, le mode, le minuteur et « Terminer ». « Terminer » n'est actif
 * que lorsque le Tuteur attend une réponse ; sinon une phrase dit pourquoi. Une session du Tuteur
 * arrêtée (`interrupted`) se dit ici, avec « Terminer » (le temps est rangé) et un nouveau départ ;
 * le minuteur s'arrête tant que la session est arrêtée.
 */
export function SessionHeader(props: SessionHeaderProps) {
  const { session, run, finishing, workMinutes, breakMinutes } = props;
  const hintId = useId();
  const interrupted = session.status === "interrupted";
  const hinted = !run.canFinish && !finishing && !interrupted;
  return (
    <header className="flex flex-col gap-3">
      <SessionTitle session={session} />
      {interrupted ? (
        <p role="status" className="rounded-lg border border-border bg-card px-3 py-2 text-sm">
          {t("study.session.interrupted")}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        {finishing ? (
          <p role="status" className="text-sm text-muted-foreground">
            {t("study.session.finishing")}
          </p>
        ) : (
          <StudyTimer
            workMinutes={workMinutes}
            breakMinutes={breakMinutes}
            onWorkedChange={run.onWorkedChange}
            storageKey={timerKey(session.id)}
            halted={interrupted}
          />
        )}
        <Button
          disabled={!run.canFinish}
          aria-describedby={hinted ? hintId : undefined}
          onClick={() => void run.finish()}
        >
          {t("study.session.finish")}
        </Button>
        {interrupted ? <NewBlockStart mode={session.mode} /> : null}
      </div>
      {hinted ? (
        <p id={hintId} className="text-sm text-muted-foreground">
          {t("study.session.finishHint")}
        </p>
      ) : null}
    </header>
  );
}
