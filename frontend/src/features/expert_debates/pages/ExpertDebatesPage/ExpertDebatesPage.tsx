import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { DebateQuestion } from "../../components/DebateQuestion";
import { useDebates } from "../../hooks/useDebates";
import { DebateDetail } from "../DebateDetail";
import { DebateHistory } from "../DebateHistory";

export function ExpertDebatesPage() {
  const { debateId = "" } = useParams();
  const { list, detail, start, judgment } = useDebates(debateId);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    title.current?.focus();
  }, [debateId]);
  const active = debateId ? detail : list;
  const error = start.error ?? judgment.error;
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      {debateId && (
        <Link to="/etudier/debats" className="self-start text-sm underline underline-offset-2">
          {t("expertDebates.back")}
        </Link>
      )}
      <h1 ref={title} tabIndex={-1} className="text-2xl font-semibold">
        {t("expertDebates.title")}
      </h1>
      {error && <InlineError message={errorMessage(error)} />}
      {debateId && detail.data ? (
        <DebateDetail debate={detail.data} saving={judgment.isPending} onSave={judgment.mutate} />
      ) : null}
      {!debateId && <DebateQuestion busy={start.isPending} onStart={start.mutate} />}
      {!debateId && list.data && <DebateHistory debates={list.data} />}
      {active.isPending && <LoadingState label={t("expertDebates.loading")} />}
      {active.isError && !active.data && (
        <ErrorState message={errorMessage(active.error)} onRetry={() => void active.refetch()} />
      )}
    </div>
  );
}
