import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface WaitingNoticeProps {
  label: string;
  hint?: string;
  /** L'attente a épuisé ses 40 relectures. */
  exhausted: boolean;
  onContinue: () => void;
}

/** « Analyse en cours… » ; après 40 relectures, une phrase honnête et un bouton pour continuer. */
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
