import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface IncidentClockProps {
  minute: number;
  ended: boolean;
  alerted: boolean;
  busy: boolean;
  onAdvance: () => void;
}

export function IncidentClock({ minute, ended, alerted, busy, onAdvance }: IncidentClockProps) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <p role="status">{t("oncall.minute", { minute })}</p>
        <Button
          aria-disabled={busy || ended}
          onClick={() => {
            if (!busy && !ended) onAdvance();
          }}
        >
          {t("oncall.advance")}
        </Button>
      </div>
      {ended && <p className="text-sm">{t("oncall.clockDone")}</p>}
      {alerted ? (
        <p role="alert" className="rounded-md border border-border px-3 py-2 font-semibold">
          {t("oncall.alert")}
        </p>
      ) : (
        <p>{t("oncall.waiting")}</p>
      )}
    </>
  );
}
