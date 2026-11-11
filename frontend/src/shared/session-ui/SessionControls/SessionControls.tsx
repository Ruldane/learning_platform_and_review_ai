import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import type { SessionStatus } from "@/shared/realtime/types";
import { Button } from "@/shared/ui/button";

interface SessionControlsProps {
  status: SessionStatus;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  /** Actions propres à un écran (ex. « Relancer un tour »). */
  extraActions?: ReactNode;
}

const FINISHED: readonly SessionStatus[] = ["completed", "failed", "cancelled"];

/** Pause si la session tourne, Reprendre si elle est en pause, Annuler tant qu'elle n'est pas terminée. */
export function SessionControls({
  status,
  onPause,
  onResume,
  onCancel,
  extraActions,
}: SessionControlsProps) {
  const finished = FINISHED.includes(status);
  if (finished && !extraActions) return null;
  return (
    <div role="group" aria-label={t("session.controls.label")} className="flex flex-wrap gap-2">
      {status === "running" ? (
        <Button variant="outline" onClick={onPause}>
          {t("session.controls.pause")}
        </Button>
      ) : null}
      {status === "paused" ? (
        <Button onClick={onResume}>{t("session.controls.resume")}</Button>
      ) : null}
      {extraActions}
      {finished ? null : (
        <Button variant="destructive" onClick={onCancel}>
          {t("session.controls.cancel")}
        </Button>
      )}
    </div>
  );
}
