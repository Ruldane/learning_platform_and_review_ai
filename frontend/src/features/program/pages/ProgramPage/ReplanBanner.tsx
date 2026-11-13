import { MessageSquareMore } from "lucide-react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { useWaitingReplan } from "../../hooks/useWaitingReplan";

/**
 * Bandeau d'un programme validé dont une replanification attend la réponse de January : il mène à
 * la proposition. Rien ne s'affiche tant que la lecture n'a pas abouti, ni en cas d'échec : le
 * bouton « Replanifier » de l'en-tête reste l'accès normal.
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
      <Link to={`/apprendre/programme/${programId}/replanification`} className={buttonVariants()}>
        {t("program.replan.open")}
      </Link>
    </div>
  );
}
