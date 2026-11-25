import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import type { SessionStatus } from "@/shared/realtime/types";
import { Button } from "@/shared/ui/button";

interface SessionControlsProps {
  status: SessionStatus;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  /** Actions specific to one screen (e.g. « Relancer un tour »). */
  extraActions?: ReactNode;
}

const FINISHED: readonly SessionStatus[] = ["completed", "failed", "cancelled", "expired"];

/** Pause while the session runs, Resume when paused, Cancel until it ends. */
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
