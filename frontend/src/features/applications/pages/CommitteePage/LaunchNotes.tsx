import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useStartCommittee } from "../../hooks/useStartCommittee";
import { PROFILE_PATH } from "../../urls";

interface LaunchNotesProps {
  start: ReturnType<typeof useStartCommittee>;
  /** Un comité tourne : la note « tu le suis ici » n'a de sens que tant qu'il tourne. */
  running: boolean;
}

/** Ce que le lancement dit : un comité déjà ouvert que l'on suit (tant qu'il tourne), un refus en toutes lettres, le profil à valider. */
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
