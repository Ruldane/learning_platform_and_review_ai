import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { DocumentRow } from "../viewTypes";
import { DocumentListItem } from "./DocumentListItem";

interface DocumentListProps {
  documents: DocumentRow[];
  /** Documents whose « déjà appris » marking is in progress: their button is disabled. */
  learningIds: string[];
  onMarkLearned: (id: string, source?: RunSource) => void;
}

/** Imported documents: status, server error message, and the « déjà appris » marking. */
export function DocumentList({ documents, learningIds, onMarkLearned }: DocumentListProps) {
  if (documents.length === 0) return <EmptyState title={t("memory.documents.empty")} />;
  return (
    <ul aria-label={t("memory.documents.title")} className="flex flex-col gap-2">
      {documents.map((document) => (
        <DocumentListItem
          key={document.id}
          document={document}
          learning={learningIds.includes(document.id)}
          onMarkLearned={onMarkLearned}
        />
      ))}
    </ul>
  );
}
