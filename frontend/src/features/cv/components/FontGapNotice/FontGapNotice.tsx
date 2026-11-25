import { t } from "@/shared/i18n/t";

interface FontGapNoticeProps {
  /** One sentence per replaced font, without the name read from the PDF. */
  gaps: string[];
}

/**
 * The original CV's fonts that were replaced, listed one by one; nothing if there are none.
 */
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
