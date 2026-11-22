import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  canSaveRules: boolean;
  canCompare: boolean;
  canSave: boolean;
  onSaveRules: () => void;
  onSave: () => void;
}

export function ComparisonButtons({
  canSaveRules,
  canCompare,
  canSave,
  onSaveRules,
  onSave,
}: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="outline" disabled={!canSaveRules} onClick={onSaveRules}>
        {t("offerComparison.saveRules")}
      </Button>
      <Button type="submit" disabled={!canCompare}>
        {t("offerComparison.compare")}
      </Button>
      <Button type="button" disabled={!canSave} onClick={onSave}>
        {t("offerComparison.save")}
      </Button>
    </div>
  );
}
