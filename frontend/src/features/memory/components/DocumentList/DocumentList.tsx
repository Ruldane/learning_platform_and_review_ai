import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { DocumentRow } from "../viewTypes";
import { DocumentListItem } from "./DocumentListItem";

interface DocumentListProps {
  documents: DocumentRow[];
  /** Documents dont le marquage « déjà appris » est en cours : leur bouton est désactivé. */
  learningIds: string[];
  onMarkLearned: (id: string) => void;
}

/** Documents importés : statut, message d'erreur du serveur, et marquage « déjà appris ». */
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
