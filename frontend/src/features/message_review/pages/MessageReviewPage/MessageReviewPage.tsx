import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readReviewSettings, saveReviewSettings, type ReviewPreferences } from "../../api";
import { MessageReviewForm } from "./MessageReviewForm";

const key = ["message-review", "settings"] as const;

export function MessageReviewPage() {
  const cache = useQueryClient();
  const [draft, setDraft] = useState<ReviewPreferences | null>(null);
  const query = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => readReviewSettings(signal),
    staleTime: 0,
  });
  const save = useMutation({
    mutationFn: saveReviewSettings,
    onSuccess: (settings) => {
      cache.setQueryData(key, settings);
      setDraft(null);
    },
  });
  if (query.isPending) return <LoadingState label={t("messageReview.loading")} />;
  if (query.isError)
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const { timezone, tokens, ...settings } = query.data;
  const values = draft ?? settings;
  const change = (patch: Partial<ReviewPreferences>) => {
    setDraft({ ...values, ...patch });
    save.reset();
  };
  return (
    <section className="grid max-w-2xl gap-4">
      <h1 className="text-2xl font-semibold">{t("messageReview.title")}</h1>
      <p>{t("messageReview.description")}</p>
      <MessageReviewForm
        values={values}
        timezone={timezone}
        tokens={tokens}
        saving={save.isPending}
        saved={save.isSuccess}
        error={save.error ? errorMessage(save.error) : null}
        onChange={change}
        onSave={() => save.mutate(values)}
      />
    </section>
  );
}
