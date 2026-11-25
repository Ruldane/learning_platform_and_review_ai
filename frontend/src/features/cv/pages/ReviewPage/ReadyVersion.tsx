import { PdfPreview } from "../../components/PdfPreview";
import type { VersionOut } from "../../types";
import { pageRange, versionPageUrl, versionPdfUrl } from "../../urls";
import { ignoredText } from "./versionTexts";

/** The ready PDF: preview, download, and what the layout could not place in it. */
export function ReadyVersion({ version, title }: { version: VersionOut; title: string }) {
  const ignored = ignoredText(version);
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
      {ignored ? (
        <p role="status" className="text-sm">
          {ignored}
        </p>
      ) : null}
    </section>
  );
}
