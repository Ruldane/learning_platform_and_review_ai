import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ProfileVersionList } from "../../components/ProfileVersionList";
import { useProfileVersions } from "../../hooks/useProfile";
import { toProfileVersionViews } from "../../toView";

/** The master profile history: never overwritten, each validation is a version. */
export function VersionsSection() {
  const query = useProfileVersions();
  return (
    <section aria-labelledby="profile-versions" className="flex flex-col gap-3">
      <h2 id="profile-versions" className="text-lg font-medium">
        {t("cv.profilePage.versions")}
      </h2>
      {query.data !== undefined ? (
        <ProfileVersionList versions={toProfileVersionViews(query.data)} />
      ) : query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : (
        <LoadingState />
      )}
    </section>
  );
}
