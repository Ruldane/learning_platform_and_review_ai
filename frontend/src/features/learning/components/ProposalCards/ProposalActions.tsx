import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ProposalView } from "../viewTypes";

export interface ProposalActionsProps {
  proposal: ProposalView;
  /** Choosing and mixing are allowed (the debate is over, nothing is in progress). */
  actionable: boolean;
  /** The card is checked for the mix. */
  ticked: boolean;
  /** Two cards are already checked: this one can no longer be checked. */
  tickLocked: boolean;
  onChoose: () => void;
  onTick: () => void;
  onShowBoard: (boardId: string) => void;
}

/** Card footer: « Choisir » (or « Parcours choisi »), « Voir au tableau », « Mélanger » box. */
export function ProposalActions({
  proposal,
  actionable,
  ticked,
  tickLocked,
  onChoose,
  onTick,
  onShowBoard,
}: ProposalActionsProps) {
  const { name, boardId } = proposal;
  return (
    <footer className="flex flex-wrap items-end gap-2">
      {proposal.chosen ? (
        <p className="font-medium text-primary">{t("learning.proposals.chosen")}</p>
      ) : (
        <Button
          disabled={!actionable}
          aria-label={t("learning.proposals.chooseNamed", { name })}
          onClick={onChoose}
        >
          {t("learning.proposals.choose")}
        </Button>
      )}
      {boardId !== null ? (
        <Button
          variant="outline"
          aria-label={t("learning.proposals.showBoardNamed", { name })}
          onClick={() => onShowBoard(boardId)}
        >
          {t("learning.proposals.showBoard")}
        </Button>
      ) : null}
      <label className="ml-auto flex items-center gap-1.5 text-xs">
        <input
          type="checkbox"
          checked={ticked}
          disabled={!actionable || (tickLocked && !ticked)}
          aria-label={t("learning.proposals.mixPickNamed", { name })}
          onChange={onTick}
        />
        <span aria-hidden="true">{t("learning.proposals.mixPick")}</span>
      </label>
    </footer>
  );
}
