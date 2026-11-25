import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useStartCommittee } from "../../hooks/useStartCommittee";
import { PROFILE_PATH } from "../../urls";

interface LaunchNotesProps {
  start: ReturnType<typeof useStartCommittee>;
  /** A committee is running: the « tu le suis ici » note only makes sense while it runs. */
  running: boolean;
}

/** What the launch says: a committee already open that is followed (while it runs), a refusal in
 * words, the profile to validate. */
export function LaunchNotes({ start, running }: LaunchNotesProps) {
  return (
    <>
      {start.resumed && running ? (
        <p role="status" className="text-sm">
          {t("applications.committeeControls.followingOpen")}
        </p>
      ) : null}
      {start.error ? <InlineError message={start.error} /> : null}
      {start.profileMissing ? (
        <Link
          to={PROFILE_PATH}
          className="w-fit text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("applications.committeeControls.openProfile")}
        </Link>
      ) : null}
    </>
  );
}
