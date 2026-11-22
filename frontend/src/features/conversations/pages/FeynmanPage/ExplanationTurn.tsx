import { t } from "@/shared/i18n/t";
import type { Run } from "@/shared/realtime/useRun";
import { InterruptCard } from "@/shared/session-ui/InterruptCard";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

export function ExplanationTurn({ run }: { run: Run }) {
  const question = run.stream.pendingInterrupt;
  return (
    <div className="flex flex-col gap-3">
      {question ? (
        <InterruptCard
          key={question.interrupt_id}
          interrupt={question}
          voice
          answered={false}
          disabled={run.actions.pending}
          onAnswer={(value) => void run.actions.resume(question.interrupt_id, value)}
        />
      ) : run.stream.status === "paused" ? (
        <Button
          type="button"
          className="self-start"
          disabled={run.actions.pending}
          onClick={() => void run.actions.resume(null, null)}
        >
          {t("feynman.resume")}
        </Button>
      ) : (
        <p role="status">{t("feynman.waiting")}</p>
      )}
      {run.actions.error && <InlineError message={run.actions.error} />}
      <Button
        type="button"
        variant="outline"
        className="self-start"
        disabled={run.actions.pending}
        onClick={() => void run.actions.cancel()}
      >
        {t("feynman.stop")}
      </Button>
    </div>
  );
}
