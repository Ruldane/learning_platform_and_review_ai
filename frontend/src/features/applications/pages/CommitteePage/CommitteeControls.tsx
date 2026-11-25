import { useState } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import type { ReadyVersion } from "../../hooks/useCvVersions";
import type { useStartCommittee } from "../../hooks/useStartCommittee";
import type { CommitteeView } from "../../types";
import { CV_VERSIONS_PATH } from "../../urls";
import { LaunchNotes } from "./LaunchNotes";
import { VersionPicker } from "./VersionPicker";

interface CommitteeControlsProps {
  /** The ready versions, most recent first; `undefined` while they load. */
  versions: ReadyVersion[] | undefined;
  versionsLoading: boolean;
  /** The version sent with the record: offered first if it is ready. */
  defaultVersionId: string | null;
  /** The followed run. */
  view: CommitteeView | undefined;
  /** A committee was just started (202) and its first read is not there yet: no second start. */
  loadingRun: boolean;
  /** The posting already has a committee: the button says « Relancer ». */
  hasRuns: boolean;
  start: ReturnType<typeof useStartCommittee>;
  onLaunch: (versionId: string) => void;
}

/** The version the last committee judged, and the prompt to re-run if a newer one exists. */
function versionNotes(versions: ReadyVersion[], view: CommitteeView | undefined) {
  if (!view) return null;
  const judged = versions.find((version) => version.id === view.cvVersionId);
  const latest = versions[0];
  const newer =
    latest && latest.id !== view.cvVersionId && (!judged || latest.number > judged.number);
  return (
    <>
      {judged ? (
        <p className="text-sm text-muted-foreground">
          {t("applications.committeeControls.judged", { number: judged.number })}
        </p>
      ) : null}
      {newer ? (
        <p className="text-sm font-medium">{t("applications.committeeControls.newer")}</p>
      ) : null}
    </>
  );
}

/** Pick the ready CV version, start or re-run the committee; refusals are stated in words. */
export function CommitteeControls({
  versions,
  versionsLoading,
  defaultVersionId,
  view,
  loadingRun,
  hasRuns,
  start,
  onLaunch,
}: CommitteeControlsProps) {
  const [chosen, setChosen] = useState<string | null>(null);
  if (versionsLoading) {
    return <p role="status">{t("applications.committeeControls.versionsLoading")}</p>;
  }
  const ready = versions ?? [];
  const fallback = ready.find((version) => version.id === defaultVersionId) ?? ready[0];
  const selected = ready.find((version) => version.id === chosen) ?? fallback;

  return (
    <div className="flex flex-col gap-3">
      {selected ? (
        <VersionPicker
          versions={ready}
          selected={selected}
          busy={start.pending || loadingRun || view?.status === "running"}
          hasRuns={hasRuns}
          pending={start.pending}
          onChoose={setChosen}
          onLaunch={onLaunch}
        />
      ) : (
        <div className="flex flex-col items-start gap-2">
          <p className="max-w-prose">{t("applications.committeeControls.noVersion")}</p>
          <Link to={CV_VERSIONS_PATH} className={buttonVariants({ variant: "outline" })}>
            {t("applications.committeeControls.openVersions")}
          </Link>
        </div>
      )}
      {versionNotes(ready, view)}
      <LaunchNotes start={start} running={loadingRun || view?.status === "running"} />
    </div>
  );
}
