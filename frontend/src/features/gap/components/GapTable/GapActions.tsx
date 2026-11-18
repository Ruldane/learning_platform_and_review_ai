import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MAX_PLAN_SKILLS } from "../viewTypes";

interface GapActionsProps {
  count: number;
  adding: boolean;
  onAddToPlan: () => void;
  onValidate?: () => void;
}

/** Sous le tableau : « Ajouter au planning » et « Je les maîtrise déjà » pour les cases cochées. */
export function GapActions({ count, adding, onAddToPlan, onValidate }: GapActionsProps) {
  const label = adding
    ? t("gap.table.adding")
    : count === 0
      ? t("gap.table.addNone")
      : t("gap.table.add", { count });
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button onClick={onAddToPlan} disabled={count === 0 || adding} aria-busy={adding}>
        {label}
      </Button>
      {onValidate ? (
        <Button variant="outline" onClick={onValidate} disabled={count === 0 || adding}>
          {count === 0 ? t("gap.table.validateNone") : t("gap.table.validate", { count })}
        </Button>
      ) : null}
      <p className="text-xs text-muted-foreground">
        {t("gap.table.limit", { max: MAX_PLAN_SKILLS })}
      </p>
    </div>
  );
}
