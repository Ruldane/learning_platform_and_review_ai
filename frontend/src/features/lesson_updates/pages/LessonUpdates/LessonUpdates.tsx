import { useEffect, useId, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { acceptUpdate, getUpdates } from "../../api";
import { UpdateProposal } from "./UpdateProposal";

export interface LessonUpdatesProps {
  lessonId: string;
  onPublication: () => void;
}

export function LessonUpdates({ lessonId, onPublication }: LessonUpdatesProps) {
  const heading = useId();
  const cache = useQueryClient();
  const key = ["lesson_updates", lessonId];
  const updates = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => getUpdates(lessonId, signal),
    refetchInterval: ({ state }) =>
      state.data?.some((item) => item.state === "preparing" || item.state === "checking")
        ? 800
        : 15000,
  });
  const approval = useMutation({
    mutationFn: (id: string) => acceptUpdate(lessonId, id),
    async onSuccess() {
      onPublication();
      await cache.invalidateQueries({ queryKey: key });
    },
  });
  const published = updates.data?.find((item) => item.state === "published")?.id;
  const seen = useRef(published);
  useEffect(() => {
    if (published && seen.current !== published) onPublication();
    seen.current = published;
  }, [onPublication, published]);
  if (!updates.data?.length) return null;

  return (
    <section aria-labelledby={heading} className="grid gap-3">
      <h2 id={heading} className="text-lg font-semibold">
        {t("lessonUpdates.title")}
      </h2>
      {approval.error && <InlineError message={errorMessage(approval.error)} />}
      {updates.data.map((item) => (
        <UpdateProposal
          key={item.id}
          item={item}
          busy={approval.isPending}
          onAccept={() => approval.mutate(item.id)}
        />
      ))}
    </section>
  );
}
