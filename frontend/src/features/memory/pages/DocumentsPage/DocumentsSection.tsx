import { errorMessage } from "@/shared/api/errors";
import type { RunSource } from "@/shared/lib/runSource";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { DocumentList } from "../../components/DocumentList";
import type { useDocuments } from "../../hooks/useDocuments";

interface DocumentsSectionProps {
  documents: ReturnType<typeof useDocuments>;
  learningIds: string[];
  onMarkLearned: (id: string, source?: RunSource) => void;
}

/** Document list: loading, failure with a retry, or the list (empty: the component's message). */
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
