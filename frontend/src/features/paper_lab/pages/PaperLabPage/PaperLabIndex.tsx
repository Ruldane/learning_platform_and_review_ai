import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { listPaperLabs } from "../../api";
import { PaperLabStart } from "./PaperLabStart";

export function PaperLabIndex() {
  const labs = useQuery({
    queryKey: ["paperLabs", "list"],
    queryFn: ({ signal }) => listPaperLabs(signal),
  });
  return (
    <>
      <PaperLabStart />
      {labs.isPending ? <LoadingState /> : null}
      {labs.isError ? (
        <ErrorState message={errorMessage(labs.error)} onRetry={() => void labs.refetch()} />
      ) : null}
      {labs.data?.length ? (
        <ul className="space-y-3 border-t pt-3">
          {labs.data.map((lab) => (
            <li key={lab.id} className="break-words">
              <Link
                to={"/apprendre/articles/" + encodeURIComponent(lab.id)}
                className="underline underline-offset-4"
              >
                {lab.title ?? lab.url}
              </Link>
              {lab.stage === "failed" ? (
                <span className="ml-3 text-sm">{t("paperLab.failedList")}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}
