import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface QuickActionsProps {
  onStart: () => void;
  onReview: () => void;
  onAddPosting: () => void;
  onCapture: () => void;
}

/** Les quatre actions rapides de l'accueil, dans l'ordre de F17 : bloc, révisions, offre, capture. */
export function QuickActions({ onStart, onReview, onAddPosting, onCapture }: QuickActionsProps) {
  return (
    <div role="group" aria-label={t("home.quick.label")} className="flex flex-wrap gap-2">
      <Button onClick={onStart}>{t("home.quick.start")}</Button>
      <Button variant="outline" onClick={onReview}>
        {t("home.quick.review")}
      </Button>
      <Button variant="outline" onClick={onAddPosting}>
        {t("home.quick.addPosting")}
      </Button>
      <Button variant="outline" onClick={onCapture}>
        {t("home.quick.capture")}
      </Button>
    </div>
  );
}
