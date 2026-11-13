import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { StudySummaryCard } from "../../components/StudySummaryCard";
import { toSummaryView } from "../../toView";
import type { StudySessionOut } from "../../types";

/** La fin d'une session : le bilan, puis où aller ensuite (réviser les fiches, revenir au départ). */
export function StudyEnd({ session }: { session: StudySessionOut }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <StudySummaryCard summary={toSummaryView(session)} />
      <div className="flex flex-wrap gap-2">
        <Link to="/etudier/revisions" className={buttonVariants()}>
          {t("study.session.reviews")}
        </Link>
        <Link to="/etudier/session" className={buttonVariants({ variant: "outline" })}>
          {t("study.session.nextBlock")}
        </Link>
      </div>
    </div>
  );
}
