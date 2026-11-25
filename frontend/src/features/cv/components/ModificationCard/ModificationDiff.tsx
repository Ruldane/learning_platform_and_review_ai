import { t } from "@/shared/i18n/t";
import { DiffSide } from "./DiffSide";
import { wordDiff } from "./wordDiff";

interface ModificationDiffProps {
  before: string;
  after: string;
}

/** « Avant » and « Après » of a modification, compared word by word. */
export function ModificationDiff({ before, after }: ModificationDiffProps) {
  const segments = wordDiff(before, after);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="flex flex-col gap-1">
        <h4 className="text-xs font-medium text-muted-foreground">{t("cv.mod.before")}</h4>
        <DiffSide segments={segments} side="before" empty={t("cv.mod.nothingBefore")} />
      </div>
      <div className="flex flex-col gap-1">
        <h4 className="text-xs font-medium text-muted-foreground">{t("cv.mod.after")}</h4>
        <DiffSide segments={segments} side="after" empty={t("cv.mod.nothingAfter")} />
      </div>
    </div>
  );
}
