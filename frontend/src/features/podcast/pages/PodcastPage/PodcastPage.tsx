import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { useLaunchSource } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { preparePodcast, readPodcast } from "../../api";
import { PodcastEpisode } from "./PodcastEpisode";

const key = ["podcast", "today"] as const;
const processing = (status?: string) => status === "queued" || status === "script";

export function PodcastPage() {
  const cache = useQueryClient();
  const source = useLaunchSource();
  const episode = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => readPodcast(signal),
    refetchInterval: ({ state }) => (processing(state.data?.status) ? 2500 : false),
  });
  const start = useMutation({
    mutationFn: () => preparePodcast(source.source),
    onSuccess: () => void cache.invalidateQueries({ queryKey: key }),
  });
  const ready = episode.data;
  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("podcast.title")}</h1>
      {episode.isPending ? <LoadingState label={t("podcast.loading")} /> : null}
      {episode.isError ? (
        <ErrorState message={errorMessage(episode.error)} onRetry={() => void episode.refetch()} />
      ) : null}
      {ready?.status === "failed" ? <InlineError message={t("podcast.failed")} /> : null}
      {start.error ? <InlineError message={errorMessage(start.error)} /> : null}
      {episode.isSuccess && (!ready || ready.status === "failed") ? (
        <div className="flex flex-wrap items-end gap-2">
          {source.menu}
          <Button disabled={start.isPending} onClick={() => start.mutate()}>
            {t("podcast.prepare")}
          </Button>
        </div>
      ) : null}
      {processing(ready?.status) ? <LoadingState label={t("podcast.pending")} /> : null}
      {ready ? <PodcastEpisode episode={ready} /> : null}
    </div>
  );
}
