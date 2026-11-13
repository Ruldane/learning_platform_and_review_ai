import { t } from "@/shared/i18n/t";
import type { FactSourceView } from "../viewTypes";

interface FactSourceBadgesProps {
  sources: FactSourceView[];
}

const ORDER: FactSourceView[] = ["cv", "linkedin", "note", "january"];

/** D'où vient un fait du profil : « CV », « LinkedIn », « Note », « Toi ». Rien sans source. */
export function FactSourceBadges({ sources }: FactSourceBadgesProps) {
  const shown = ORDER.filter((source) => sources.includes(source));
  if (shown.length === 0) return null;
  return (
    <ul aria-label={t("cv.sources.label")} className="flex flex-wrap gap-1">
      {shown.map((source) => (
        <li
          key={source}
          data-source={source}
          className="rounded-md border bg-muted px-1.5 py-0.5 text-xs font-medium"
        >
          {t(`cv.source.${source}`)}
        </li>
      ))}
    </ul>
  );
}
