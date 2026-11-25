import { t } from "@/shared/i18n/t";
import { LEVEL_COLORS, LEVEL_KEYS } from "../levels";

/** Legend of the graph: each level colour with its written name, and what the size means. */
export function SkillLegend() {
  return (
    <div className="flex flex-col gap-1 text-sm">
      <ul aria-label={t("skills.legend.label")} className="flex flex-wrap gap-x-4 gap-y-1">
        {LEVEL_KEYS.map((key) => (
          <li key={key} className="flex items-center gap-1.5">
            <span
              data-swatch
              aria-hidden="true"
              className="size-3 rounded-sm"
              style={{ backgroundColor: LEVEL_COLORS[key] }}
            />
            {t(`skills.level.${key}`)}
          </li>
        ))}
      </ul>
      <p className="text-muted-foreground">{t("skills.legend.color")}</p>
      <p className="text-muted-foreground">{t("skills.legend.size")}</p>
    </div>
  );
}
