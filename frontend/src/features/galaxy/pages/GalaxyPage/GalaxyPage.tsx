import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readGalaxy } from "../../api";
import { GalaxyWorkspace } from "../GalaxyWorkspace";

export function GalaxyPage() {
  const map = useQuery({
    queryKey: ["galaxy"],
    queryFn: ({ signal }) => readGalaxy(signal),
  });
  if (map.isPending) return <LoadingState label={t("galaxy.loading")} />;
  if (!map.data) {
    return <ErrorState message={errorMessage(map.error)} onRetry={() => void map.refetch()} />;
  }
  const graph = map.data;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("galaxy.title")}</h1>
      {graph.nodes.length ? (
        <>
          <p>{t("galaxy.intro")}</p>
          {graph.target_label && <p>{t("galaxy.target", { label: graph.target_label })}</p>}
          <GalaxyWorkspace graph={graph} />
        </>
      ) : (
        <p>{t("galaxy.empty")}</p>
      )}
    </div>
  );
}
