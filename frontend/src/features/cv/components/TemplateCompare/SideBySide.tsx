import { t } from "@/shared/i18n/t";
import { PageImage } from "./PageImage";

interface SideBySideProps {
  originalPages: string[];
  renderPages: string[];
}

/** The pages of the original and the recreated template, in two columns, page by page. */
export function SideBySide({ originalPages, renderPages }: SideBySideProps) {
  const count = Math.max(originalPages.length, renderPages.length);
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
        <h4 className="text-sm font-medium">{t("cv.template.columnOriginal")}</h4>
        <h4 className="text-sm font-medium">{t("cv.template.columnRender")}</h4>
      </div>
      {Array.from({ length: count }, (_, index) => {
        const n = index + 1;
        return (
          <section
            key={n}
            aria-label={t("cv.template.page", { n })}
            className="grid grid-cols-2 gap-4"
          >
            <PageImage
              src={originalPages[index]}
              alt={t("cv.template.originalAlt", { n })}
              missing={t("cv.template.missingPage", { n })}
            />
            <PageImage
              src={renderPages[index]}
              alt={t("cv.template.renderAlt", { n })}
              missing={t("cv.template.missingPage", { n })}
            />
          </section>
        );
      })}
    </div>
  );
}
