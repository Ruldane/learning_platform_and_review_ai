import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ChatMarkdown } from "@/shared/ui/ChatMarkdown";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { answerHunt, readHunt } from "../../api";
import { HuntCorrections } from "../../components/HuntCorrections";
import { AnswerEditor } from "./AnswerEditor";
function useHunt(huntId: string) {
  const client = useQueryClient();
  const key = ["lessonHunts", huntId] as const;
  const hunt = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => readHunt(huntId, signal),
    refetchInterval: ({ state }) =>
      state.data?.stage === "preparing" || state.data?.stage === "reviewing" ? 900 : false,
  });
  const answer = useMutation({
    mutationFn: (responses: string[]) => answerHunt(huntId, responses),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  return { hunt, answer };
}

export function ActiveHunt({ huntId }: { huntId: string }) {
  const { hunt, answer } = useHunt(huntId);
  if (hunt.isPending) return <LoadingState />;
  if (hunt.isError)
    return <ErrorState message={errorMessage(hunt.error)} onRetry={() => void hunt.refetch()} />;
  const data = hunt.data;
  const canAnswer = data.stage === "ready" || (data.stage === "failed" && data.exercise !== null);
  return (
    <>
      <h2 className="text-lg font-semibold">{data.title}</h2>
      {data.stage === "preparing" || data.stage === "reviewing" ? (
        <p role="status">
          {t(data.stage === "preparing" ? "lessonHunt.preparing" : "lessonHunt.reviewing")}
        </p>
      ) : null}
      {data.stage === "failed" ? <p role="alert">{t("lessonHunt.failed")}</p> : null}
      {data.stage === "failed" && !data.exercise ? (
        <Link
          to={`/learn/lessons/${encodeURIComponent(data.lesson_id)}/errors`}
          className="underline"
        >
          {t("lessonHunt.retry")}
        </Link>
      ) : null}
      {data.exercise ? <ChatMarkdown>{data.exercise}</ChatMarkdown> : null}
      {canAnswer ? (
        <AnswerEditor
          initial={data.responses}
          submitting={answer.isPending}
          submit={(values) => answer.mutate(values)}
        />
      ) : null}
      {answer.isError ? <p role="alert">{errorMessage(answer.error)}</p> : null}
      {data.stage === "complete" ? (
        <HuntCorrections
          answers={data.assessment?.answers ?? []}
          corrections={data.corrections ?? []}
        />
      ) : null}
    </>
  );
}
