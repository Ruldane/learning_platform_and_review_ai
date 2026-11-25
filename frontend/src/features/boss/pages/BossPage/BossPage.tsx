import { useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useBoss } from "../../hooks/useBoss";
import { BossWorkspace } from "../BossWorkspace";

export function BossPage() {
  const { programId = "" } = useParams();
  const { query, start, submit } = useBoss(programId);
  const title = useRef<HTMLHeadingElement>(null);
  if (query.isPending) return <LoadingState label={t("boss.loading")} />;
  if (!query.data)
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const { attempt, eligible } = query.data;
  const failure = start.error ?? submit.error ?? query.error;
  return (
    <div className="flex max-w-3xl flex-col items-start gap-5">
      <Link
        className="text-sm underline underline-offset-2"
        to={`/learn/programs/${encodeURIComponent(programId)}`}
      >
        {t("boss.back")}
      </Link>
      <h1 ref={title} tabIndex={-1} className="text-2xl font-semibold">
        {t("boss.title")}
      </h1>
      <p>{query.data.title}</p>
      {failure && <InlineError message={errorMessage(failure)} />}
      {attempt ? (
        <BossWorkspace
          attempt={attempt}
          receivedAt={query.dataUpdatedAt}
          sending={submit.isPending}
          onSubmit={() => submit.mutate()}
        />
      ) : (
        <>
          <p>{t(eligible ? "boss.ready" : "boss.locked")}</p>
          {eligible && (
            <Button
              aria-disabled={start.isPending}
              onClick={() => {
                if (!start.isPending)
                  start.mutate(undefined, { onSuccess: () => title.current?.focus() });
              }}
            >
              {t("boss.start")}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
