import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useStartInterview } from "../../hooks/useStartInterview";
import { PROFILE_PATH } from "../../urls";

export function StartControls({ launcher }: { launcher: ReturnType<typeof useStartInterview> }) {
  return (
    <div className="flex flex-col items-start gap-2">
      {launcher.launchMenu}
      <Button type="submit" disabled={launcher.pending}>
        {t(
          launcher.pending
            ? "applications.interviewSetup.starting"
            : "applications.interviewSetup.start",
        )}
      </Button>
      {launcher.error ? <InlineError message={launcher.error} /> : null}
      {launcher.profileMissing ? (
        <Link
          to={PROFILE_PATH}
          className="text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("applications.interviewSetup.openProfile")}
        </Link>
      ) : null}
    </div>
  );
}
