import type { ReactNode } from "react";
import { InlineError } from "@/shared/ui/states/InlineError";
import { RadarForm } from "../../components/RadarForm";
import type { RadarRunRequestView } from "../../components/viewTypes";
import type { LaunchErrors } from "../../errors";

interface RadarLaunchProps {
  /** Role and area suggested by the server (setting, else last goal). */
  defaults: { role: string; zone: string };
  running: boolean;
  launchMenu?: ReactNode;
  errors: LaunchErrors | null;
  onRun: (request: RadarRunRequestView) => void;
}

/**
 * A sweep launch: the pre-filled form. It reads its values only once: its `key`
 * follows the suggested values, so it restarts from them when they arrive or change.
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
