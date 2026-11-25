import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { StudySummaryCard } from "../../components/StudySummaryCard";
import { toSummaryView } from "../../toView";
import type { StudySessionOut } from "../../types";

/** The end of a session: the summary, then where to go next (review cards, back to start). */
export function StudyEnd({ session }: { session: StudySessionOut }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <StudySummaryCard summary={toSummaryView(session)} />
      <div className="flex flex-wrap gap-2">
        <Link to="/study/reviews" className={buttonVariants()}>
          {t("study.session.reviews")}
        </Link>
        <Link to="/study/session" className={buttonVariants({ variant: "outline" })}>
          {t("study.session.nextBlock")}
        </Link>
      </div>
    </div>
  );
}
