import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface QuizPreparingProps {
  /** La préparation dure plus que prévu (40 relectures sans résultat). */
  late: boolean;
  onKeepWaiting: () => void;
}

/** Le quiz se prépare : un état de chargement ; trop long, on le dit et on propose d'attendre encore. */
export function QuizPreparing({ late, onKeepWaiting }: QuizPreparingProps) {
  if (!late) return <LoadingState label={t("quiz.page.preparing")} />;
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-3 py-2"
    >
      <p className="text-sm">{t("quiz.page.preparingLate")}</p>
      <Button variant="outline" onClick={onKeepWaiting}>
        {t("quiz.page.keepWaiting")}
      </Button>
    </div>
  );
}
