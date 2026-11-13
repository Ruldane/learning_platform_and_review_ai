import { t } from "@/shared/i18n/t";
import type { PostingAnalysisView } from "../viewTypes";

interface RequirementsProps {
  items: PostingAnalysisView["requirements"];
}

/** Les exigences de l'offre, chacune marquée « Exigée » ou « Souhaitée ». */
export function Requirements({ items }: RequirementsProps) {
  return (
    <section className="flex flex-col gap-1">
      <h4 className="text-sm font-medium">{t("gap.analysis.requirements")}</h4>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("gap.analysis.none")}</p>
      ) : (
        <ul className="flex flex-col gap-1 text-sm">
          {items.map((item, index) => (
            <li key={`${item.text}-${index}`} className="flex gap-2">
              <span className="w-20 shrink-0 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {item.required ? t("gap.analysis.required") : t("gap.analysis.wished")}
              </span>
              <span>{item.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
