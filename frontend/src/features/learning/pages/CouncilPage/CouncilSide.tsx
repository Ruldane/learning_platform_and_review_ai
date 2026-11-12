import { SourcesPanel } from "@/shared/session-ui";
import { CouncilTabs } from "../../components/CouncilTabs";
import type { useCouncilData } from "../../hooks/useCouncilData";
import type { useCouncilSession } from "../../hooks/useCouncilSession";
import type { useCouncilTabs } from "../../hooks/useCouncilTabs";
import { BoardPane } from "./BoardPane";
import { ProposalsPane } from "./ProposalsPane";
import { useProposalsPane } from "./useProposalsPane";

interface CouncilSideProps {
  session: ReturnType<typeof useCouncilSession>;
  data: ReturnType<typeof useCouncilData>;
  tabs: ReturnType<typeof useCouncilTabs>;
}

/**
 * Colonne de droite : le tableau du Scribe, les sources (pages et praticiens à part, jamais
 * mélangés ni comptés ensemble) et les propositions.
 */
export function CouncilSide({ session, data, tabs }: CouncilSideProps) {
  const { saved, edit, boards, sources } = data;
  const searching = session.progress.stage === "research" && session.stream.status === "running";
  const proposals = useProposalsPane(session, data, tabs.showBoard);
  return (
    <CouncilTabs
      active={tabs.tab}
      onChange={tabs.setTab}
      board={
        <BoardPane
          states={boards}
          loading={saved.isPending}
          failed={saved.isError}
          onRetry={() => void saved.refetch()}
          activeId={tabs.boardId}
          onSelect={tabs.setBoardId}
          onSendEdit={edit.send}
          sending={edit.pending}
          sendError={edit.error}
        />
      }
      sources={<SourcesPanel model={sources} pending={searching} />}
      proposals={<ProposalsPane {...proposals} />}
    />
  );
}
