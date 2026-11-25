import { t } from "@/shared/i18n/t";
import type { FactRefView } from "../viewTypes";

/** The master-profile facts the change relies on; nothing if it cites none. */
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
