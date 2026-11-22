import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { listPrograms } from "../../api";
import { DossierList } from "./DossierList";
import { Suggestions } from "./Suggestions";

export function ContributionsPage() {
  const [program, setProgram] = useState("");
  const query = useQuery({
    queryKey: ["contributions", "programs"],
    queryFn: ({ signal }) => listPrograms(signal),
  });
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("contributions.title")}</h1>
      <DossierList />
      {query.isPending ? <LoadingState /> : null}
      {query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.data?.length === 0 ? <p>{t("contributions.noProgram")}</p> : null}
      {query.data?.length ? (
        <label className="flex max-w-sm flex-col gap-1 text-sm font-medium">
          {t("contributions.program")}
          <select
            value={program}
            onChange={(event) => setProgram(event.target.value)}
            className={fieldClass}
          >
            <option value="">{t("contributions.choose")}</option>
            {query.data.map(({ id, title }) => (
              <option key={id} value={id}>
                {title}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {program ? <Suggestions programId={program} key={program} /> : null}
    </div>
  );
}
