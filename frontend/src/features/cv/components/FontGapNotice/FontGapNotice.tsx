import { t } from "@/shared/i18n/t";

interface FontGapNoticeProps {
  /** Une phrase par police remplacée, sans le nom lu dans le PDF. */
  gaps: string[];
}

/** Les polices du CV d'origine qui ont été remplacées, dites une par une ; rien s'il n'y en a pas. */
export function FontGapNotice({ gaps }: FontGapNoticeProps) {
  if (gaps.length === 0) return null;
  return (
    <aside
      aria-label={t("cv.fontGap.title")}
      className="flex flex-col gap-2 rounded-xl border border-border bg-muted/50 p-3 text-sm"
    >
      <h3 className="font-medium">{t("cv.fontGap.title")}</h3>
      <ul className="list-disc pl-5">
        {gaps.map((gap, index) => (
          <li key={index}>{gap}</li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">{t("cv.fontGap.hint")}</p>
    </aside>
  );
}
