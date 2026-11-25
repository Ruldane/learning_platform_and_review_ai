import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { VectorMap } from "../../components/VectorMap";
import { ImportEmptyState } from "../ImportEmptyState";
import { useMemoryMap } from "../../hooks/useMemoryMap";

/** 2D memory map: a click on a point opens the item in the explorer. */
export function MemoryMapPage() {
  const navigate = useNavigate();
  const map = useMemoryMap();

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("memory.page.mapTitle")}</h1>
        <p className="mt-2 text-muted-foreground">{t("memory.page.mapIntro")}</p>
      </header>
      {map.isError ? (
        <ErrorState message={errorMessage(map.error)} onRetry={() => void map.refetch()} />
      ) : !map.data ? (
        <LoadingState />
      ) : map.data.points.length === 0 ? (
        <ImportEmptyState title={t("memory.map.empty")} />
      ) : (
        <VectorMap
          points={map.data.points}
          truncated={map.data.truncated}
          onOpen={(id) => void navigate(`/memory?item=${encodeURIComponent(id)}`)}
        />
      )}
    </div>
  );
}
