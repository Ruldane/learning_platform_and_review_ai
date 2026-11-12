import { Download } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { ResourceView } from "../viewTypes";

/** La copie locale (PDF) si elle existe, sinon la fiche de lecture. */
export function ResourceAttachment({ resource }: { resource: ResourceView }) {
  if (resource.localCopyUrl) {
    return (
      <a
        href={resource.localCopyUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 self-start text-sm underline underline-offset-2"
      >
        <Download aria-hidden="true" className="size-3.5" />
        {t("lessons.resources.localCopy")}
        <span className="sr-only"> : {resource.title}</span>
      </a>
    );
  }
  return resource.note ? (
    <p className="text-sm">{t("lessons.resources.readingNote", { note: resource.note })}</p>
  ) : null;
}
