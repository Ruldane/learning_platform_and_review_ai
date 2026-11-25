import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { usePostingTitles, useVersions } from "../../hooks/useVersions";
import { PostingVersions } from "./PostingVersions";
import { groupByPosting } from "./groupByPosting";

/**
 * All CV versions (`/career/cv/versions`), grouped by posting: the list, the preview and
 * the download of a version, and the link to its review.
 */
export function VersionsPage() {
  const navigate = useNavigate();
  const versions = useVersions();
  const postings = usePostingTitles();
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">{t("cv.versionsPage.title")}</h1>
      {versions.data === undefined ? (
        versions.isError ? (
          <ErrorState
            message={errorMessage(versions.error)}
            onRetry={() => void versions.refetch()}
          />
        ) : (
          <LoadingState label={t("cv.versionsPage.loading")} />
        )
      ) : versions.data.length === 0 ? (
        <EmptyState
          title={t("cv.versionsPage.emptyTitle")}
          description={t("cv.versionsPage.emptyHint")}
          action={{
            label: t("cv.versionsPage.emptyAction"),
            onClick: () => void navigate("/career/postings"),
          }}
        />
      ) : (
        groupByPosting(versions.data, postings.data ?? []).map((group) => (
          <PostingVersions key={group.postingId} group={group} />
        ))
      )}
    </div>
  );
}
