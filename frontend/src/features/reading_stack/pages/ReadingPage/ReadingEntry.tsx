import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { getReading, markReading } from "../../api";
import { readingKeys } from "../../queryKeys";
import { PassageCard } from "./PassageCard";
import { ReadingActions } from "./ReadingActions";
import { ReadingArticle } from "./ReadingArticle";

export function ReadingEntry({ id }: { id: string }) {
  const [passage, setPassage] = useState("");
  const client = useQueryClient();
  const queryKey = readingKeys.detail(id);
  const query = useQuery({ queryKey, queryFn: ({ signal }) => getReading(id, signal) });
  const mark = useMutation({
    mutationFn: (read: boolean) => markReading(id, read),
    onSuccess: (article) => {
      client.setQueryData(queryKey, { ...article, annotations: query.data?.annotations });
      void client.invalidateQueries({ queryKey: readingKeys.items });
      void client.invalidateQueries({ queryKey: ["home", "brief"] });
    },
  });
  if (query.isPending) return <LoadingState label={t("reading.articleLoading")} />;
  if (query.isError)
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const article = query.data;
  return (
    <article
      aria-labelledby="reading-article-title"
      className="flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <ReadingArticle article={article} onPassage={setPassage} />
      {article.text ? <PassageCard id={article.id} passage={passage} /> : null}
      <Button
        type="button"
        variant="outline"
        className="self-start"
        disabled={mark.isPending}
        onClick={() => mark.mutate(!article.read_at)}
      >
        {t(article.read_at ? "reading.markUnread" : "reading.markRead")}
      </Button>
      {mark.error ? <InlineError message={errorMessage(mark.error)} /> : null}
      <ReadingActions article={article} />
    </article>
  );
}
