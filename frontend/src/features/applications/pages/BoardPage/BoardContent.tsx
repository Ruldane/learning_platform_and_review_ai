import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ApplicationTable } from "../../components/ApplicationTable";
import { KanbanBoard } from "../../components/KanbanBoard";
import { useApplications } from "../../hooks/useApplications";
import { applicationPath, NEW_APPLICATION_PATH } from "../../urls";
import type { BoardView } from "./ViewSwitch";
import type { StatusView } from "../../types";

interface BoardContentProps {
  view: BoardView;
  onMove: (id: string, status: StatusView) => void;
}

/** Les fiches selon l'état de la lecture : chargement, erreur, rien encore, tableau de suivi ou tableau. */
export function BoardContent({ view, onMove }: BoardContentProps) {
  const navigate = useNavigate();
  const query = useApplications();
  const open = (id: string) => void navigate(applicationPath(id));

  if (query.isPending) return <LoadingState label={t("applications.boardPage.loading")} />;
  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  if (query.data.length === 0) {
    return (
      <EmptyState
        title={t("applications.boardPage.emptyTitle")}
        description={t("applications.boardPage.emptyDescription")}
        action={{
          label: t("applications.boardPage.new"),
          onClick: () => void navigate(NEW_APPLICATION_PATH),
        }}
      />
    );
  }
  return view === "board" ? (
    <KanbanBoard applications={query.data} onMove={onMove} onOpen={open} />
  ) : (
    <ApplicationTable applications={query.data} onOpen={open} />
  );
}
