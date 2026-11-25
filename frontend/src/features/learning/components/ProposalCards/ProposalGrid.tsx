import type { ProposalView } from "../viewTypes";
import { ProposalCard } from "./ProposalCard";

interface ProposalGridProps {
  /** Already sorted by rank. */
  proposals: ProposalView[];
  actionable: boolean;
  picked: string[];
  /** Number of cards to check to mix: beyond it, the other boxes are disabled. */
  mixSize: number;
  onChoose: (proposalId: string) => void;
  onTick: (proposalId: string) => void;
  onShowBoard: (boardId: string) => void;
}

/** The cards side by side (shared grid, sections aligned by `subgrid`). */
export function ProposalGrid({
  proposals,
  actionable,
  picked,
  mixSize,
  onChoose,
  onTick,
  onShowBoard,
}: ProposalGridProps) {
  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: "repeat(auto-fit, minmax(17rem, 1fr))" }}
    >
      {proposals.map((proposal) => (
        <ProposalCard
          key={proposal.id}
          proposal={proposal}
          actionable={actionable}
          ticked={picked.includes(proposal.id)}
          tickLocked={picked.length >= mixSize}
          onChoose={() => onChoose(proposal.id)}
          onTick={() => onTick(proposal.id)}
          onShowBoard={onShowBoard}
        />
      ))}
    </div>
  );
}
