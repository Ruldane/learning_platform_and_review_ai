import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ExternalLink } from "@/shared/ui/ExternalLink";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { getOffer, planSkills } from "../../api";
import { OfferGapForm } from "./OfferGapForm";

export function CompatibleOfferPage() {
  const { runId = "", ref = "" } = useParams();
  const query = useQuery({
    queryKey: ["compatible-offer", runId, ref],
    queryFn: ({ signal }) => getOffer(runId, ref, signal),
  });
  const plan = useMutation({ mutationFn: (skills: string[]) => planSkills(runId, ref, skills) });
  if (query.isPending) return <LoadingState />;
  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  const offer = query.data;
  return (
    <section className="grid max-w-3xl gap-4">
      <Link to="/" className="w-fit underline">{t("compatibleOffers.brief")}</Link>
      <h1 className="text-2xl font-semibold">{offer.title ?? t("home.offers.untitled")}</h1>
      {offer.company ? <p>{offer.company}</p> : null}
      <p>{t("compatibleOffers.score", { score: offer.score })}</p>
      <ExternalLink href={offer.url}>{t("compatibleOffers.source")}</ExternalLink>
      <OfferGapForm key={runId + ref} rows={offer.rows} busy={plan.isPending} onSubmit={plan.mutate} />
      {plan.error ? <InlineError message={errorMessage(plan.error)} /> : null}
      {plan.data ? (
        <div role="status">
          <Link className="underline" to={"/apprendre/programme/" + plan.data.program_id + "/replanification"}>
            {t("compatibleOffers.openPlan")}
          </Link>
        </div>
      ) : null}
    </section>
  );
}
