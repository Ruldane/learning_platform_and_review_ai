import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { PdfPreview } from "../../components/PdfPreview";
import { useVersion } from "../../hooks/useVersions";
import { pageRange, versionPageUrl, versionPdfUrl } from "../../urls";

interface OpenedVersionProps {
  versionId: string;
  onClose: () => void;
}

/** L'aperçu d'une version ouverte : ses pages et son téléchargement, ou pourquoi il n'y en a pas. */
export function OpenedVersion({ versionId, onClose }: OpenedVersionProps) {
  const query = useVersion(versionId);
  const version = query.data;
  if (version === undefined) {
    return query.isError ? (
      <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
    ) : (
      <LoadingState />
    );
  }
  return (
    <div className="flex flex-col gap-2 rounded-xl border bg-card p-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">{t("cv.versionsPage.preview", { number: version.number })}</h3>
        <Button variant="outline" size="sm" onClick={onClose}>
          {t("cv.versionsPage.closePreview")}
        </Button>
      </div>
      {version.status === "ready" ? (
        <PdfPreview
          pages={pageRange(version.page_count ?? 0, (n) => versionPageUrl(version.id, n))}
          pageCount={version.page_count ?? 0}
          originalPageCount={version.original_page_count}
          filename={version.filename}
          downloadUrl={versionPdfUrl(version.id)}
        />
      ) : (
        <p className="text-sm text-muted-foreground">{t("cv.versionsPage.notReady")}</p>
      )}
    </div>
  );
}
