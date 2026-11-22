import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readRoutines, type RoutineAction } from "../../api";
import { ROUTINES } from "../../queryKeys";
import { RoutineEditor } from "./RoutineEditor";

import { RoutineSelector } from "./RoutineSelector";

export function RoutinesPage() {
  const [action, setAction] = useState<RoutineAction>("due_reviews");
  const rules = useQuery({ queryKey: ROUTINES, queryFn: readRoutines, refetchInterval: 5000 });
  const rule = rules.data?.find((item) => item.action === action);
  return (
    <section className="flex max-w-2xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("routines.title")}</h1>
      {rules.isPending ? <LoadingState label={t("routines.loading")} /> : null}
      {rules.isError ? (
        <ErrorState message={errorMessage(rules.error)} onRetry={() => void rules.refetch()} />
      ) : null}
      {rules.isSuccess && (
        <>
          <RoutineSelector selected={action} onSelect={setAction} />
          <RoutineEditor key={action} action={action} rule={rule} />
        </>
      )}
    </section>
  );
}
