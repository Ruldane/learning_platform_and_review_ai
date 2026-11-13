import { t } from "@/shared/i18n/t";
import type { FactRefView } from "../viewTypes";

/** Les faits du profil maître sur lesquels s'appuie la modification ; rien si elle n'en cite pas. */
export function Facts({ facts }: { facts: FactRefView[] }) {
  if (facts.length === 0) return null;
  return (
    <div className="flex flex-col gap-1 text-sm">
      <h4 className="text-xs font-medium text-muted-foreground">{t("cv.mod.facts")}</h4>
      <ul className="list-disc pl-5">
        {facts.map((fact) => (
          <li key={fact.id}>{fact.label}</li>
        ))}
      </ul>
    </div>
  );
}
