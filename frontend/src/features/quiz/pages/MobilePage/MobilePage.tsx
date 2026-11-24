import { Link } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useMobileAccess } from "./useMobileReview";
import { MobileStudy } from "./MobileStudy";

export function MobilePage() {
  const { snapshot, pinned, offline, loading, error } = useMobileAccess();
  const withoutAccount = error instanceof ApiError && error.status === 401;
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 p-4 sm:p-6">
      <h1 className="text-2xl font-semibold">{t("mobile.title")}</h1>
      {!offline ? <Link to="/" className="self-start underline">{t("mobile.home")}</Link> : null}
      {offline ? <p role="status">{t("mobile.offline")}</p> : null}
      {loading ? <p role="status">{t("mobile.loading")}</p> : null}
      {withoutAccount ? <Link to="/login" className="underline">{t("mobile.login")}</Link> : null}
      {error && !withoutAccount ? <InlineError message={errorMessage(error)} /> : null}
      {snapshot ? <MobileStudy key={snapshot.owner} snapshot={snapshot} pinned={pinned} offline={offline} /> : null}
      {offline && !snapshot ? <p>{t("mobile.unprepared")}</p> : null}
    </main>
  );
}
