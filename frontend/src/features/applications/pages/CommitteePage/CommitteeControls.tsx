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
  /** Les versions prêtes, la plus récente d'abord ; `undefined` tant qu'elles se chargent. */
  versions: ReadyVersion[] | undefined;
  versionsLoading: boolean;
  /** La version envoyée avec la fiche : proposée en premier si elle est prête. */
  defaultVersionId: string | null;
  /** L'exécution suivie. */
  view: CommitteeView | undefined;
  /** Un comité vient d'être lancé (202) et sa première lecture n'est pas encore là : pas de second lancement. */
  loadingRun: boolean;
  /** L'offre a déjà un comité : le bouton dit « Relancer ». */
  hasRuns: boolean;
  start: ReturnType<typeof useStartCommittee>;
  onLaunch: (versionId: string) => void;
}

/** La version jugée par le dernier comité, et la phrase qui invite à relancer si une plus récente existe. */
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

/** Choisir la version prête du CV de l'offre, lancer ou relancer le comité ; les refus sont dits en toutes lettres. */
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
      <LaunchNotes start={start} />
    </div>
  );
}
