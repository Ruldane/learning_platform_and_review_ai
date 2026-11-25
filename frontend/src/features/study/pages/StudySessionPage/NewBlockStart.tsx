import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useStartStudy } from "../../hooks/useStartStudy";
import type { StudySessionOut } from "../../types";

/**
 * « Commencer un nouveau bloc » from a stopped session: the start is made from here (the back end
 * saves or cancels the stopped session), not from home, which leads back here. No block
 * planned for today: the home page offers to choose a lesson.
 */
export function NewBlockStart({ mode }: { mode: StudySessionOut["mode"] }) {
  const navigate = useNavigate();
  const starter = useStartStudy(() => void navigate("/study/session"));
  return (
    <div className="flex flex-col gap-2">
      {starter.launchMenu}
      <Button
        variant="outline"
        disabled={starter.pending}
        onClick={() => void starter.start({ mode })}
      >
        {t("study.session.newBlock")}
      </Button>
      {starter.error ? <InlineError message={starter.error} /> : null}
    </div>
  );
}
