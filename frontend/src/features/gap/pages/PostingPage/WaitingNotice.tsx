import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface WaitingNoticeProps {
  label: string;
  hint?: string;
  /** The wait has used up its 40 re-reads. */
  exhausted: boolean;
  onContinue: () => void;
}

/** « Analyse en cours… »; after 40 re-reads, an honest sentence and a button to continue. */
export function WaitingNotice({ label, hint, exhausted, onContinue }: WaitingNoticeProps) {
  if (exhausted) {
    return (
      <div role="status" className="flex flex-col items-start gap-2">
        <p>{t("gap.posting.tooLong")}</p>
        <Button variant="outline" onClick={onContinue}>
          {t("gap.posting.tooLongAction")}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <LoadingState label={label} />
      {hint ? <p className="text-center text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
