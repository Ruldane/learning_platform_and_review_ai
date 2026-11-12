import type { ProposalView } from "../viewTypes";
import { ProposalCard } from "./ProposalCard";

interface ProposalGridProps {
  /** Déjà triées par rang. */
  proposals: ProposalView[];
  actionable: boolean;
  picked: string[];
  /** Nombre de cartes à cocher pour mélanger : au-delà, les autres cases sont désactivées. */
  mixSize: number;
  onChoose: (proposalId: string) => void;
  onTick: (proposalId: string) => void;
  onShowBoard: (boardId: string) => void;
}

/** Les cartes côte à côte (grille commune, rubriques alignées par `subgrid`). */
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
