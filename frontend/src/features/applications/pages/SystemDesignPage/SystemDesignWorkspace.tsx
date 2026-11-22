import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { useRun } from "@/shared/realtime/useRun";
import { Button } from "@/shared/ui/button";
import type { Design } from "../../systemDesignApi";
import { SystemDesignBoard } from "./SystemDesignBoard";
import { SystemDesignReview } from "./SystemDesignReview";
import { SystemDesignSubject } from "./SystemDesignSubject";
import { SystemDesignSubmission } from "./SystemDesignSubmission";

export function SystemDesignWorkspace({
  design,
  refresh,
}: {
  design: Design;
  refresh: () => void;
}) {
  const [local, setLocal] = useState<Design["board"] | null>(null);
  const [dirty, setDirty] = useState(false);
  const run = useRun(design.status === "running" ? design.session_id : null, refresh);
  const frozen = design.version_id !== null;
  const board = frozen || !local || design.board.step >= local.step ? design.board : local;
  const active = design.status === "running";
  const draft = active && !frozen;
  return (
    <div className="flex flex-col gap-4">
      <SystemDesignSubject subject={design.subject} />
      <SystemDesignBoard
        board={board}
        readOnly={!draft}
        onBoardSaved={setLocal}
        onDirtyChange={setDirty}
      />
      {draft && <SystemDesignSubmission board={board} dirty={dirty} run={run} />}
      {active && run.stream.status === "paused" && (
        <Button
          type="button"
          variant="outline"
          className="self-start"
          disabled={run.actions.pending}
          onClick={() => void run.actions.resume(null, null)}
        >
          {t("systemDesign.resume")}
        </Button>
      )}
      {active && frozen && <p role="status">{t("systemDesign.reviewing")}</p>}
      {design.defense && <p className="max-w-3xl whitespace-pre-wrap">{design.defense}</p>}
      {design.review && <SystemDesignReview review={design.review} proof={design.proof_saved} />}
      {design.status === "failed" && <p role="status">{t("systemDesign.failed")}</p>}
    </div>
  );
}
