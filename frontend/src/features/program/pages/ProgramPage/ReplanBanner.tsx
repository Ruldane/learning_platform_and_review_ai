import { MessageSquareMore } from "lucide-react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { useWaitingReplan } from "../../hooks/useWaitingReplan";

/**
 * Banner for a validated program whose replan awaits January's answer: it leads to
 * the proposal. Nothing shows until the read has succeeded, nor on failure: the
 * « Replanifier » button in the header remains the normal way in.
 */
export function ReplanBanner({ programId, enabled }: { programId: string; enabled: boolean }) {
  const waiting = useWaitingReplan(programId, enabled);
  if (!enabled || !waiting.data) return null;
  return (
    <div role="status" className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-4">
      <MessageSquareMore aria-hidden="true" className="size-5 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{t("program.replan.waitingTitle")}</p>
        <p className="text-sm text-muted-foreground">{t("program.replan.waitingHint")}</p>
      </div>
      <Link to={`/learn/programs/${programId}/replan`} className={buttonVariants()}>
        {t("program.replan.open")}
      </Link>
    </div>
  );
}
