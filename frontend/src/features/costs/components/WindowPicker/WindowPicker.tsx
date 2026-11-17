import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { COST_WINDOWS, type CostWindow } from "../viewTypes";

interface WindowPickerProps {
  value: CostWindow;
  onChange: (days: CostWindow) => void;
}

/** Les fenêtres du rapport : 7, 30 ou 90 jours (la choisie est annoncée par `aria-pressed`). */
export function WindowPicker({ value, onChange }: WindowPickerProps) {
  return (
    <div role="group" aria-label={t("costs.report.window.label")} className="flex gap-2">
      {COST_WINDOWS.map((days) => (
        <Button
          key={days}
          variant={days === value ? "default" : "outline"}
          aria-pressed={days === value}
          onClick={() => onChange(days)}
        >
          {t("costs.report.window.option", { days })}
        </Button>
      ))}
    </div>
  );
}
