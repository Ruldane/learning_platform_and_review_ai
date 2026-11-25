import { t } from "@/shared/i18n/t";
import type { MissingSkillView } from "../viewTypes";

interface TopMissingListProps {
  items: MissingSkillView[];
  onOpenSkill: (skill: string) => void;
}

function line(item: MissingSkillView): string {
  return t("gap.top.item", {
    skill: item.skill,
    postings:
      item.postings === 1
        ? t("gap.top.postingOne")
        : t("gap.top.postingMany", { count: item.postings }),
    required:
      item.requiredIn === 0
        ? t("gap.top.requiredNever")
        : t("gap.top.requiredIn", { count: item.requiredIn }),
  });
}

/** The skills most often missing: « Python — 5 offres, exigée dans 4 ». */
export function TopMissingList({ items, onOpenSkill }: TopMissingListProps) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("gap.top.empty")}</p>;
  }
  return (
    <ol aria-label={t("gap.top.label")} className="flex flex-col gap-1">
      {items.map((item) => (
        <li key={item.skill}>
          <button
            type="button"
            onClick={() => onOpenSkill(item.skill)}
            className="w-full rounded-lg border bg-card px-3 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring"
          >
            {line(item)}
          </button>
        </li>
      ))}
    </ol>
  );
}
