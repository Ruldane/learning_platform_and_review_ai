import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { downloadLinks } from "../../api";
import { BookActions } from "../../components/BookActions";
import { useBook } from "../../useBook";

export function Edition({ programId, pollMs }: { programId: string; pollMs: number }) {
  const { edition, request } = useBook(programId, pollMs);
  if (edition.isPending) return <LoadingState />;
  if (!edition.data) {
    return (
      <ErrorState message={errorMessage(edition.error)} onRetry={() => void edition.refetch()} />
    );
  }
  const book = edition.data;
  const problem = request.isError
    ? errorMessage(request.error)
    : book.status === "failed"
      ? t("book.edition.failed")
      : null;
  return (
    <BookActions
      queued={book.status === "queued"}
      busy={request.isPending}
      problem={problem}
      files={book.available ? downloadLinks(programId) : null}
      chapters={book.chapters ?? 0}
      onRequest={() => request.mutate(programId)}
    />
  );
}
