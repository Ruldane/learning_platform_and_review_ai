import { useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { TopMissingList } from "../../components/TopMissingList";
import { useTopMissing } from "../../hooks/useTopMissing";
import { toMissingViews } from "../../toView";

const SKILLS_PATH = "/skills";
const POSTINGS_PATH = "/career/postings";

/**
 * Gaps (`/career/gaps`): the 10 skills most often missing from the
 * postings added, with a link to the skills map. A skill leads to the map.
 */
export function GapOverviewPage() {
  const navigate = useNavigate();
  const query = useTopMissing();
  const items = useMemo(() => (query.data ? toMissingViews(query.data) : null), [query.data]);

  let body;
  if (items === null) {
    body = query.isError ? (
      <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
    ) : (
      <LoadingState label={t("gap.overview.loading")} />
    );
  } else if (items.length === 0) {
    body = (
      <EmptyState
        title={t("gap.overview.emptyTitle")}
        description={t("gap.overview.emptyDescription")}
        action={{
          label: t("gap.overview.emptyAction"),
          onClick: () => void navigate(POSTINGS_PATH),
        }}
      />
    );
  } else {
    body = <TopMissingList items={items} onOpenSkill={() => void navigate(SKILLS_PATH)} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("gap.overview.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("gap.overview.intro")}</p>
      </header>
      {body}
      <div className="flex flex-wrap gap-2">
        <Link to={SKILLS_PATH} className={buttonVariants({ variant: "outline" })}>
          {t("gap.overview.map")}
        </Link>
        <Link to={POSTINGS_PATH} className={buttonVariants({ variant: "outline" })}>
          {t("gap.overview.postings")}
        </Link>
      </div>
    </div>
  );
}
