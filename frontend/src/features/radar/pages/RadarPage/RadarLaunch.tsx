import type { ReactNode } from "react";
import { InlineError } from "@/shared/ui/states/InlineError";
import { RadarForm } from "../../components/RadarForm";
import type { RadarRunRequestView } from "../../components/viewTypes";
import type { LaunchErrors } from "../../errors";

interface RadarLaunchProps {
  /** Poste et zone proposés par le serveur (réglage, sinon dernier objectif). */
  defaults: { role: string; zone: string };
  running: boolean;
  launchMenu?: ReactNode;
  errors: LaunchErrors | null;
  onRun: (request: RadarRunRequestView) => void;
}

/**
 * Le lancement d'un relevé : le formulaire prérempli. Il ne lit ses valeurs qu'une fois : sa `key`
 * suit les valeurs proposées, il repart donc de celles-ci quand elles arrivent ou changent.
 */
export function RadarLaunch({ defaults, running, errors, onRun, launchMenu }: RadarLaunchProps) {
  return (
    <div className="flex flex-col gap-3">
      <RadarForm
        key={`${defaults.role}\u0000${defaults.zone}`}
        role={defaults.role}
        zone={defaults.zone}
        running={running}
        launchMenu={launchMenu}
        onRun={onRun}
        roleError={errors?.role}
        zoneError={errors?.zone}
      />
      {errors?.general ? <InlineError message={errors.general} /> : null}
    </div>
  );
}
