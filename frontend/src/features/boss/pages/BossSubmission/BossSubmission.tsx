import type { components } from "@/shared/api/schema";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

type State = components["schemas"]["BossAttemptOut"]["state"];

interface BossSubmissionProps {
  state: State;
  canSubmit: boolean;
  sending: boolean;
  onSubmit: () => void;
}

const status = {
  building: "boss.submitHelp",
  expired: "boss.expired",
  reviewing: "boss.reviewing",
  review_failed: "boss.reviewFailed",
  graded: "boss.graded",
} as const;

export function BossSubmission({ state, canSubmit, sending, onSubmit }: BossSubmissionProps) {
  const canSend = !sending && (state === "review_failed" || (state === "building" && canSubmit));
  return (
    <div className="flex flex-col items-start gap-2">
      <p role="status">{t(status[state])}</p>
      <Button
        aria-disabled={!canSend}
        onClick={() => {
          if (canSend) onSubmit();
        }}
      >
        {t(state === "review_failed" ? "boss.retry" : "boss.submit")}
      </Button>
    </div>
  );
}
