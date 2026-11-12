import { t } from "@/shared/i18n/t";
import type { ProposalView } from "../viewTypes";
import { MixBar } from "./MixBar";
import { ProposalGrid } from "./ProposalGrid";
import { useMixSelection } from "./useMixSelection";

interface ProposalCardsProps {
  proposals: ProposalView[];
  /** January peut choisir, mélanger ou relancer (le débat est fini). */
  canChoose: boolean;
  /** Le Conseil propose un autre tour (absent au plafond de tours : l'interruption n'en offre plus). */
  canAnotherRound?: boolean;
  /** Une action est en cours : tout est désactivé, sauf « Voir au tableau ». */
  busy: boolean;
  onChoose: (proposalId: string) => void;
  /** Reçoit les deux identifiants dans l'ordre des cartes. */
  onMix: (firstId: string, secondId: string) => void;
  onAnotherRound: () => void;
  onShowBoard: (boardId: string) => void;
}

const MIX_SIZE = 2;

/**
 * Les 2 à 3 propositions du Conseil côte à côte (SPEC 3.2), mêmes rubriques alignées. January en
 * choisit une, en mélange deux (cases à cocher, puis « Mélanger ces deux parcours ») ou demande un
 * autre tour. Tant que `canChoose` est faux (ou qu'une action est en cours), rien de tout cela n'est
 * possible ; « Voir au tableau » reste ouvert. Présentationnel : la page reçoit les actions.
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
  // Un parcours est déjà choisi : plus rien à décider ici.
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
