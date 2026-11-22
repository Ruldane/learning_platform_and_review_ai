import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readSurpriseSettings, saveSurpriseSettings, type SurprisePreferences } from "../../api";
import { SurpriseForm } from "./SurpriseForm";

const key = ["surprise-interview", "settings"] as const;

export function SurpriseSettingsPage() {
  const cache = useQueryClient();
  const [draft, edit] = useState<SurprisePreferences | null>(null);
  const query = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => readSurpriseSettings(signal),
    staleTime: 0,
  });
  const save = useMutation({
    mutationFn: saveSurpriseSettings,
    onSuccess: (data) => {
      cache.setQueryData(key, data);
      edit(null);
    },
  });
  if (query.isPending) return <LoadingState label={t("surpriseInterview.loading")} />;
  if (query.isError)
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const { enabled, role, token_id } = query.data;
  const values = draft ?? { enabled, role, token_id };
  return (
    <section className="grid max-w-2xl gap-4">
      <h1 className="text-2xl font-semibold">{t("surpriseInterview.title")}</h1>
      <p>{t("surpriseInterview.description")}</p>
      <SurpriseForm
        values={values}
        settings={query.data}
        saving={save.isPending}
        saved={save.isSuccess}
        error={save.error ? errorMessage(save.error) : null}
        onChange={(patch) => {
          edit({ ...values, ...patch });
          save.reset();
        }}
        onSave={() => save.mutate(values)}
      />
    </section>
  );
}
