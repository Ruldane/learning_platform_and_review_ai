import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useStudyReturn } from "../../useStudyReturn";
import { ReturnBlock } from "../ReturnBlock";
import { ReturnReminder } from "../ReturnReminder";

export function StudyReturnPage() {
  const result = useStudyReturn();
  return (
    <section className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("studyReturn.title")}</h1>
      {result.isPending && <LoadingState />}
      {result.isError && (
        <ErrorState message={errorMessage(result.error)} onRetry={() => void result.refetch()} />
      )}
      {result.data && (
        <>
          <ReturnBlock plan={result.data.plan} />
          <ReturnReminder state={result.data} />
        </>
      )}
    </section>
  );
}
