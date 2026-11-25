import { useId, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface SendRowProps {
  pending: boolean;
  launchMenu?: ReactNode;
  /** Nothing is sent: the action is ignored (`aria-disabled`, focus stays on the button). */
  blocked: boolean;
  hasKey: boolean;
  /** What prevents or qualifies sending, stated and tied to the button; empty: nothing to say. */
  reasons: string[];
  onGoToKey: () => void;
}

/** « Importer mes documents », the path to a key when there is none, and the reasons stated. */
export function SendRow({
  pending,
  blocked,
  hasKey,
  reasons,
  onGoToKey,
  launchMenu,
}: SendRowProps) {
  const reasonId = useId();
  return (
    <>
      <div className="flex flex-wrap items-end gap-3">
        {hasKey ? launchMenu : null}
        <Button
          type="submit"
          aria-disabled={blocked}
          aria-describedby={reasons.length > 0 ? reasonId : undefined}
        >
          {pending ? t("onboarding.cv.pending") : t("onboarding.cv.submit")}
        </Button>
        {hasKey ? null : (
          <Button type="button" variant="outline" onClick={onGoToKey}>
            {t("onboarding.cv.goToKey")}
          </Button>
        )}
      </div>
      {reasons.length > 0 ? (
        <p id={reasonId} className="text-sm text-muted-foreground">
          {reasons.join(" ")}
        </p>
      ) : null}
    </>
  );
}
