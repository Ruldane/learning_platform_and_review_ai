import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { PdfPreview } from "../../components/PdfPreview";
import type { useGenerate } from "../../hooks/useGenerate";
import { pageRange, versionPageUrl, versionPdfUrl } from "../../urls";
import type { CvReviewOut, VersionOut } from "../../types";

interface VersionPanelProps {
  review: CvReviewOut;
  /** La dernière version de la revue, ou `null` si aucun PDF n'a été demandé. */
  version: VersionOut | null;
  generate: ReturnType<typeof useGenerate>;
}

/**
 * Le PDF de la dernière version : en rendu, prêt (aperçu et téléchargement), trop long (« Autoriser
 * une page de plus ») ou en échec (« Réessayer »). Une nouvelle génération n'est possible que
 * pendant la question de sortie, jamais pendant un rendu.
 */
export function VersionPanel({ review, version, generate }: VersionPanelProps) {
  if (version === null) return null;
  const canRegenerate = review.waiting_output && !generate.pending;
  const title = t("cv.reviewPage.versionNumber", { number: version.number });
  switch (version.status) {
    case "rendering":
      return <LoadingState label={t("cv.reviewPage.pdfRendering")} />;
    case "ready":
      return (
        <section aria-label={title} className="flex flex-col gap-2">
          <h3 className="font-medium">{title}</h3>
          <PdfPreview
            pages={pageRange(version.page_count ?? 0, (n) => versionPageUrl(version.id, n))}
            pageCount={version.page_count ?? 0}
            originalPageCount={version.original_page_count}
            filename={version.filename}
            downloadUrl={versionPdfUrl(version.id)}
          />
        </section>
      );
    case "pages_exceeded":
      return (
        <section aria-label={title} className="flex flex-col items-start gap-2">
          <p
            role="alert"
            className="rounded-lg border-2 border-foreground/60 bg-muted/60 p-2 text-sm"
          >
            {t("cv.reviewPage.pagesExceeded", { count: version.page_count ?? 0 })}
          </p>
          <Button disabled={!canRegenerate} onClick={() => generate.generate(true)}>
            {t("cv.reviewPage.allowExtra")}
          </Button>
        </section>
      );
    default:
      return (
        <section aria-label={title} className="flex flex-col items-start gap-2">
          <InlineError message={version.failure_reason ?? t("cv.reviewPage.pdfFailedFallback")} />
          <Button
            variant="outline"
            disabled={!canRegenerate}
            onClick={() => generate.generate(false)}
          >
            {t("cv.reviewPage.retryGenerate")}
          </Button>
        </section>
      );
  }
}
