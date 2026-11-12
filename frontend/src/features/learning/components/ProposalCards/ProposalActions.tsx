import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ProposalView } from "../viewTypes";

export interface ProposalActionsProps {
  proposal: ProposalView;
  /** Choisir et mélanger sont permis (le débat est fini, rien n'est en cours). */
  actionable: boolean;
  /** La carte est cochée pour le mélange. */
  ticked: boolean;
  /** Deux cartes sont déjà cochées : celle-ci ne peut plus l'être. */
  tickLocked: boolean;
  onChoose: () => void;
  onTick: () => void;
  onShowBoard: (boardId: string) => void;
}

/** Pied d'une carte : « Choisir » (ou « Parcours choisi »), « Voir au tableau », case « Mélanger ». */
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
