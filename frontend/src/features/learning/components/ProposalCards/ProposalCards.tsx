import { t } from "@/shared/i18n/t";
import type { ProposalView } from "../viewTypes";
import { MixBar } from "./MixBar";
import { ProposalGrid } from "./ProposalGrid";
import { useMixSelection } from "./useMixSelection";

interface ProposalCardsProps {
  proposals: ProposalView[];
  /** January can choose, mix or rerun (the debate is over). */
  canChoose: boolean;
  /** The Council offers another round, except at the round cap (no interruption option). */
  canAnotherRound?: boolean;
  /** An action is in progress: everything is disabled except « Voir au tableau ». */
  busy: boolean;
  onChoose: (proposalId: string) => void;
  /** Receives the two ids in card order. */
  onMix: (firstId: string, secondId: string) => void;
  onAnotherRound: () => void;
  onShowBoard: (boardId: string) => void;
}

const MIX_SIZE = 2;

/**
 * The Council's 2 to 3 proposals side by side (SPEC 3.2), same aligned sections. January
 * picks one, mixes two (checkboxes, then « Mélanger ces deux parcours ») or asks for
 * another round. While `canChoose` is false (or an action is running), none of this is
 * possible; « Voir au tableau » stays open. Presentational: the page receives the actions.
 */
export function ProposalCards({
  proposals,
  canChoose,
  canAnotherRound = true,
  busy,
  onChoose,
  onMix,
  onAnotherRound,
  onShowBoard,
}: ProposalCardsProps) {
  const ordered = [...proposals].sort((a, b) => a.rank - b.rank);
  const { picked, toggle } = useMixSelection(ordered);
  const actionable = canChoose && !busy;
  // A path is already chosen: nothing left to decide here.
  const decided = ordered.some((proposal) => proposal.chosen);

  if (ordered.length === 0) {
    return <p className="text-muted-foreground">{t("learning.proposals.empty")}</p>;
  }
  return (
    <section
      aria-label={t("learning.proposals.label")}
      aria-busy={busy}
      className="flex flex-col gap-4"
    >
      <ProposalGrid
        proposals={ordered}
        actionable={actionable}
        picked={picked}
        mixSize={MIX_SIZE}
        onChoose={onChoose}
        onTick={toggle}
        onShowBoard={onShowBoard}
      />
      {decided ? null : (
        <MixBar
          picked={picked.length}
          size={MIX_SIZE}
          canChoose={canChoose}
          canAnotherRound={canAnotherRound}
          actionable={actionable}
          onMix={() => onMix(picked[0] ?? "", picked[1] ?? "")}
          onAnotherRound={onAnotherRound}
        />
      )}
    </section>
  );
}
