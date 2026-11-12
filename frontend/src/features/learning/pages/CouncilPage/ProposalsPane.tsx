import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ProposalCards } from "../../components/ProposalCards";
import type { ProposalView } from "../../components/viewTypes";

interface ProposalsPaneProps {
  proposals: ProposalView[] | undefined;
  loading: boolean;
  failed: boolean;
  onRetry: () => void;
  /** La question du choix est posée : on peut choisir, mélanger ou relancer. */
  canChoose: boolean;
  /** L'interruption offre « autre tour » (elle n'en offre plus au plafond de tours). */
  canAnotherRound: boolean;
  busy: boolean;
  /** Conflit relu (propositions périmées, Conseil qui n'attend pas…) : une information, pas une erreur. */
  notice: string | null;
  error: string | null;
  onChoose: (proposalId: string) => void;
  onMix: (firstId: string, secondId: string) => void;
  onAnotherRound: () => void;
  onShowBoard: (boardId: string) => void;
}

/** L'onglet Propositions : chargement, erreur avec « Réessayer », information de conflit, cartes. */
export function ProposalsPane(props: ProposalsPaneProps) {
  const { proposals, loading, failed, onRetry, notice, error, ...cards } = props;
  if (failed && proposals === undefined) {
    return <ErrorState message={t("errors.generic")} onRetry={onRetry} />;
  }
  if (loading || proposals === undefined) {
    return <LoadingState label={t("learning.council.proposalsLoading")} />;
  }
  return (
    <div className="flex flex-col gap-3">
      {notice ? (
        <p role="status" className="rounded-lg border border-border bg-card px-3 py-2 text-sm">
          {notice}
        </p>
      ) : null}
      {error ? <InlineError message={error} /> : null}
      <ProposalCards proposals={proposals} {...cards} />
    </div>
  );
}
