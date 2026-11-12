import { ChevronLeft, ChevronRight } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { WeekView } from "../../types";

interface WeekPickerProps {
  weeks: WeekView[];
  /** Rang de la semaine affichée. */
  rank: number;
  onChange: (rank: number) => void;
}

/** Choix de la semaine affichée : précédente, suivante, ou l'une quelconque par la liste. */
export function WeekPicker({ weeks, rank, onChange }: WeekPickerProps) {
  const index = weeks.findIndex((week) => week.rank === rank);
  const go = (offset: number) => {
    const target = weeks[index + offset];
    if (target) onChange(target.rank);
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        type="button"
        variant="outline"
        size="icon"
        aria-label={t("program.weekPicker.previous")}
        disabled={index <= 0}
        onClick={() => go(-1)}
      >
        <ChevronLeft aria-hidden="true" />
      </Button>
      <label className="flex min-w-0 items-center gap-2 text-sm">
        <span className="sr-only">{t("program.weekPicker.label")}</span>
        <select
          value={rank}
          onChange={(event) => onChange(Number(event.target.value))}
          className={fieldClass}
        >
          {weeks.map((week) => (
            <option key={week.rank} value={week.rank}>
              {t("program.weekPicker.option", { rank: week.rank, theme: week.theme })}
            </option>
          ))}
        </select>
      </label>
      <Button
        type="button"
        variant="outline"
        size="icon"
        aria-label={t("program.weekPicker.next")}
        disabled={index === -1 || index >= weeks.length - 1}
        onClick={() => go(1)}
      >
        <ChevronRight aria-hidden="true" />
      </Button>
    </div>
  );
}
