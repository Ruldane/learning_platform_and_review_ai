import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SessionStatus } from "@/shared/realtime/types";
import { Button, buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

const OUTCOME = {
  completed: "capture.run.completed",
  failed: "capture.run.failed",
  cancelled: "capture.run.cancelled",
} as const;

interface CaptureEndProps {
  status: SessionStatus;
  /** The reason for a failure, in plain text; `null` otherwise. */
  failure: string | null;
  onAgain: () => void;
  onClose: () => void;
}

/** The end of a capture: what happened, the link to the journal and « Nouvelle capture ». */
export function CaptureEnd({ status, failure, onAgain, onClose }: CaptureEndProps) {
  const outcome = status === "failed" || status === "cancelled" ? status : "completed";
  return (
    <div className="flex flex-col gap-2 rounded-xl border bg-card p-3">
      <p role="status" className="font-semibold">
        {t(OUTCOME[outcome])}
      </p>
      {failure ? <InlineError message={failure} /> : null}
      <div className="flex flex-wrap gap-2">
        <Link to="/study/journal" onClick={onClose} className={buttonVariants()}>
          {t("capture.run.journal")}
        </Link>
        <Button variant="outline" onClick={onAgain}>
          {t("capture.run.again")}
        </Button>
      </div>
    </div>
  );
}
