import { t } from "@/shared/i18n/t";
import { levelKey } from "../levels";
import type { SkillDetailView } from "../viewTypes";

/** Niveau, domaine et autres noms de la compétence. */
export function SkillSummary({ detail }: { detail: SkillDetailView }) {
  return (
    <div className="flex flex-col gap-1 text-sm">
      <p>{t("skills.drawer.level", { level: t(`skills.level.${levelKey(detail.level)}`) })}</p>
      <p className="text-muted-foreground">
        {t("skills.drawer.domain", { domain: detail.domain })}
      </p>
      {detail.synonyms.length > 0 ? (
        <p className="text-muted-foreground">
          {t("skills.drawer.synonyms", { names: detail.synonyms.join(", ") })}
        </p>
      ) : null}
    </div>
  );
}
