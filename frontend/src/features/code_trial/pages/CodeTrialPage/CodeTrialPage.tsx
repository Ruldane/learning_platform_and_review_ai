import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useCodeTrial } from "../../hooks/useCodeTrial";
import { TrialDossier } from "./TrialDossier";

export function CodeTrialPage() {
  const { sessionId = "", trialId } = useParams();
  const { trial, open, decide } = useCodeTrial(sessionId, trialId);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [trialId]);
  const data = trial.data;
  const error = open.error ?? decide.error;
  const busy = open.isPending || decide.isPending;
  return (
    <div className="grid max-w-4xl gap-4">
      <Link
        to={`/code/${encodeURIComponent(sessionId)}`}
        className="justify-self-start text-sm underline underline-offset-4"
      >
        {t("codeTrial.back")}
      </Link>
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        {t("codeTrial.title")}
      </h1>
      {error && <InlineError message={errorMessage(error)} />}
      {trial.isPending && <LoadingState label={t("codeTrial.loading")} />}
      {trial.isError && !data && (
        <ErrorState message={errorMessage(trial.error)} onRetry={() => void trial.refetch()} />
      )}
      {data && (
        <TrialDossier
          key={data.id}
          data={data}
          busy={busy}
          onOpen={() => open.mutate()}
          onVerdict={(verdict) => decide.mutate({ id: data.id, verdict })}
        />
      )}
      {data === null && (
        <div className="grid justify-items-start gap-3 rounded-xl border bg-card p-4">
          <p>{t("codeTrial.description")}</p>
          <Button type="button" disabled={busy} onClick={() => open.mutate()}>
            {t("codeTrial.start")}
          </Button>
        </div>
      )}
    </div>
  );
}
