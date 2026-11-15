import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useStartKit } from "../../hooks/useStartKit";
import type { KitPieceView } from "../../types";
import { kitZipUrl, PROFILE_PATH } from "../../urls";

interface KitControlsProps {
  applicationId: string;
  pieces: KitPieceView[];
  running: boolean;
  start: ReturnType<typeof useStartKit>;
  onStart: () => void;
}

function startLabel(pending: boolean, produced: boolean): string {
  if (pending) return t("applications.kitPage.starting");
  return t(produced ? "applications.kitPage.relaunch" : "applications.kitPage.generate");
}

/** Générer (ou relancer) le kit et télécharger l'archive ; les raisons d'un refus sont dites en toutes lettres. */
export function KitControls({ applicationId, pieces, running, start, onStart }: KitControlsProps) {
  const produced = pieces.some((piece) => piece.status !== "pending");
  const archivable = pieces.some(
    (piece) => piece.status === "ready" || piece.status === "to_check",
  );
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        {running ? null : (
          <Button type="button" disabled={start.pending} onClick={onStart}>
            {startLabel(start.pending, produced)}
          </Button>
        )}
        {archivable ? (
          <Button asChild variant="outline">
            <a href={kitZipUrl(applicationId)} download>
              {t("applications.kitPage.archive")}
            </a>
          </Button>
        ) : null}
      </div>
      {produced && !running ? (
        <p className="max-w-prose text-sm text-muted-foreground">
          {t("applications.kitPage.keepEdited")}
        </p>
      ) : null}
      {archivable ? (
        <p className="max-w-prose text-sm text-muted-foreground">
          {t("applications.kitPage.archiveHint")}
        </p>
      ) : null}
      {start.resumed && running ? (
        <p role="status" className="text-sm">
          {t("applications.kitPage.followingOpen")}
        </p>
      ) : null}
      {start.error ? <InlineError message={start.error} /> : null}
      {start.profileMissing ? (
        <Link
          to={PROFILE_PATH}
          className="w-fit text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("applications.kitPage.openProfile")}
        </Link>
      ) : null}
    </div>
  );
}
