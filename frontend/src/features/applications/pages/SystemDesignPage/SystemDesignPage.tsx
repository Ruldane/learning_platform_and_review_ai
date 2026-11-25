import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readDesign } from "../../systemDesignApi";
import { SystemDesignStart } from "./SystemDesignStart";
import { SystemDesignWorkspace } from "./SystemDesignWorkspace";

export function SystemDesignPage() {
  const { interviewId } = useParams();
  const query = useQuery({
    queryKey: ["system-design", interviewId ?? "current"],
    queryFn: ({ signal }) => readDesign(interviewId, signal),
    refetchInterval: ({ state }) => (state.data?.status === "running" ? 1800 : false),
  });
  const refresh = () => void query.refetch();
  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-2">
        <Link to="/applications/interview" className="w-fit text-sm underline underline-offset-4">
          {t("systemDesign.back")}
        </Link>
        <h1 className="text-2xl font-semibold">{t("systemDesign.title")}</h1>
      </header>
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState message={errorMessage(query.error)} onRetry={refresh} />}
      {query.data && (
        <SystemDesignWorkspace key={query.data.id} design={query.data} refresh={refresh} />
      )}
      {query.isSuccess && query.data?.status !== "running" && <SystemDesignStart />}
    </section>
  );
}
