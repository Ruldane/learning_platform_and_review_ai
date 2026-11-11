import { errorMessage } from "@/shared/api/errors";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { DocumentList } from "../../components/DocumentList";
import type { useDocuments } from "../../hooks/useDocuments";

interface DocumentsSectionProps {
  documents: ReturnType<typeof useDocuments>;
  learningIds: string[];
  onMarkLearned: (id: string) => void;
}

/** Liste des documents : chargement, échec avec nouvel essai, ou liste (vide : message du composant). */
export function DocumentsSection({ documents, learningIds, onMarkLearned }: DocumentsSectionProps) {
  if (documents.isError) {
    return (
      <ErrorState
        message={errorMessage(documents.error)}
        onRetry={() => void documents.refetch()}
      />
    );
  }
  if (!documents.data) return <LoadingState />;
  return (
    <DocumentList
      documents={documents.data}
      learningIds={learningIds}
      onMarkLearned={onMarkLearned}
    />
  );
}
