import { t } from "@/shared/i18n/t";

interface PdfPreviewProps {
  /** The images of the pages of the generated PDF (no embedded PDF reader). */
  pages: string[];
  pageCount: number;
  originalPageCount: number;
  /** The name of the file to download, as the server gives it. */
  filename: string;
  downloadUrl: string;
}

function pagesText(pageCount: number, original: number): string {
  if (pageCount === original) {
    return pageCount === 1 ? t("cv.pdf.same.one") : t("cv.pdf.same.many", { count: pageCount });
  }
  if (pageCount > original) return t("cv.pdf.more", { count: pageCount, original });
  return pageCount === 1
    ? t("cv.pdf.less.one", { original })
    : t("cv.pdf.less.many", { count: pageCount, original });
}

/**
 * Preview of the generated CV: images of its pages, the page count compared with the original
 * CV (a warning if it has more) and the PDF download link.
 */
export function PdfPreview({
  pages,
  pageCount,
  originalPageCount,
  filename,
  downloadUrl,
}: PdfPreviewProps) {
  const exceeded = pageCount > originalPageCount;
  return (
    <section aria-label={t("cv.pdf.label")} className="flex flex-col gap-3">
      <p
        role={exceeded ? "alert" : "status"}
        className={
          exceeded
            ? "rounded-lg border-2 border-foreground/60 bg-muted/60 p-2 text-sm font-medium"
            : "text-sm"
        }
      >
        {pagesText(pageCount, originalPageCount)}
      </p>
      <a
        href={downloadUrl}
        download={filename}
        className="w-fit text-sm font-medium text-primary underline underline-offset-4"
      >
        {t("cv.pdf.download", { filename })}
      </a>
      {pages.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("cv.pdf.empty")}</p>
      ) : (
        <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
          {pages.map((src, index) => (
            <img
              key={index}
              src={src}
              alt={t("cv.pdf.pageAlt", { n: index + 1, total: pages.length })}
              loading="lazy"
              className="w-full rounded-lg border bg-white"
            />
          ))}
        </div>
      )}
    </section>
  );
}
