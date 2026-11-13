import { t } from "@/shared/i18n/t";

interface PdfPreviewProps {
  /** Les images des pages du PDF généré (pas de lecteur PDF embarqué). */
  pages: string[];
  pageCount: number;
  originalPageCount: number;
  /** Le nom du fichier à télécharger, tel que le serveur le donne. */
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
 * L'aperçu du CV généré : les images de ses pages, le nombre de pages comparé à celui du CV
 * d'origine (avertissement s'il en a plus) et le lien de téléchargement du PDF.
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
