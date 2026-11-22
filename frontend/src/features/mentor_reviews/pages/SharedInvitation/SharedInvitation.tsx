import { useMutation, useQuery } from "@tanstack/react-query";
import { useId } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { sendComment, sharedWork, type GuestReply } from "../../api";
import { GuestFeedback } from "../GuestFeedback";
import { ProofCopy } from "../ProofCopy";

export function SharedInvitation({ token }: { token: string }) {
  const id = useId();
  const work = useQuery({
    queryKey: ["mentor_reviews", "guest", id],
    queryFn: ({ signal }) => sharedWork(token, signal),
    enabled: !!token,
    retry: false,
    gcTime: 0,
    refetchInterval: 15_000,
  });
  const comment = useMutation({
    mutationFn: (reply: GuestReply) => sendComment(token, reply),
    onError: () => { void work.refetch(); },
  });
  const unavailable = !token || (work.error instanceof ApiError && work.error.status === 404);
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-5 p-5">
      <h1 className="text-2xl font-semibold">{t("mentorReviews.sharedTitle")}</h1>
      {unavailable && <p role="status">{t("mentorReviews.missingLink")}</p>}
      {!unavailable && work.isPending && <LoadingState />}
      {!unavailable && work.error && <InlineError message={errorMessage(work.error)} />}
      {!unavailable && work.data && !work.isError && (
        <>
          <p className="text-muted-foreground">{t("mentorReviews.sharedIntro")}</p>
          <ProofCopy manifest={work.data.manifest} digest={work.data.digest} />
          <GuestFeedback proofs={work.data.manifest.proofs}
            pending={comment.isPending} onSubmit={(reply) => comment.mutate(reply)} />
          {comment.isSuccess && <p role="status">{t("mentorReviews.sent")}</p>}
          {comment.error && <InlineError message={errorMessage(comment.error)} />}
        </>
      )}
    </main>
  );
}
