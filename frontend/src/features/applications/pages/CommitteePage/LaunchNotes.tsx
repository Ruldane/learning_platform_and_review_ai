import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useStartCommittee } from "../../hooks/useStartCommittee";
import { PROFILE_PATH } from "../../urls";

/** Ce que le lancement dit : un comité déjà ouvert que l'on suit, un refus en toutes lettres, le profil à valider. */
export function LaunchNotes({ start }: { start: ReturnType<typeof useStartCommittee> }) {
  return (
    <>
      {start.resumed ? (
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
