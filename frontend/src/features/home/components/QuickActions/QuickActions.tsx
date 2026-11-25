import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface QuickActionsProps {
  onStart: () => void;
  onReview: () => void;
  onAddPosting: () => void;
  onCapture: () => void;
}

/** The four home quick actions, in F17 order: block, reviews, offer, capture. */
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
