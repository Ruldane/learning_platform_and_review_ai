import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { getOptions, getWeeks, sharedWeeksKey } from "../../api";
import { ProposalCard } from "../ProposalCard";
import { WeekForm } from "../WeekForm";

export function SharedPlanningPage() {
  const options = useQuery({
    queryKey: ["interprogram-planning-options"],
    queryFn: ({ signal }) => getOptions(signal),
  });
  const weeks = useQuery({ queryKey: sharedWeeksKey, queryFn: ({ signal }) => getWeeks(signal) });
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("interprogramPlanning.title")}</h1>
      {options.isPending && <LoadingState />}
      {options.isError && (
        <ErrorState message={errorMessage(options.error)} onRetry={() => void options.refetch()} />
      )}
      {options.data &&
        (options.data.length < 2 ? (
          <p>{t("interprogramPlanning.tooFew")}</p>
        ) : (
          <WeekForm options={options.data} />
        ))}
      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t("interprogramPlanning.list")}</h2>
        {weeks.isPending && <LoadingState />}
        {weeks.isError && (
          <ErrorState message={errorMessage(weeks.error)} onRetry={() => void weeks.refetch()} />
        )}
        {weeks.data?.length === 0 && <p>{t("interprogramPlanning.empty")}</p>}
        {weeks.data?.map((week) => (
          <ProposalCard key={week.id} week={week} />
        ))}
      </section>
    </section>
  );
}
