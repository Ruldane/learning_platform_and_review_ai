import { useRef, type ComponentType } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useFolders } from "../../hooks/useFolders";
import { FolderCard } from "./FolderCard";
import { FolderForm } from "./FolderForm";
import { SyncTokenPanel } from "./SyncTokenPanel";

export function BrainPage({ conversation: Conversation }: { conversation?: ComponentType }) {
  const name = useRef<HTMLInputElement>(null);
  const { folders, status, add, toggle, remove } = useFolders(() => name.current?.focus());
  if (folders.isPending) return <LoadingState label={t("brain.loading")} />;
  if (folders.isError && !folders.data)
    return (
      <ErrorState message={errorMessage(folders.error)} onRetry={() => void folders.refetch()} />
    );
  const error = add.error ?? toggle.error ?? remove.error ?? folders.error ?? status.error;
  const busy = toggle.isPending || remove.isPending;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("brain.title")}</h1>
      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t("brain.folders")}</h2>
        <FolderForm nameRef={name} busy={add.isPending} onAdd={(data) => add.mutateAsync(data)} />
        {error ? <InlineError message={errorMessage(error)} /> : null}
        {folders.data?.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("brain.empty")}</p>
        ) : null}
        <div className="grid max-w-4xl gap-3 md:grid-cols-2">
          {folders.data?.map((folder) => (
            <FolderCard
              key={folder.id}
              folder={folder}
              busy={busy}
              status={status.data?.find((item) => item.id === folder.id)}
              onToggle={() => toggle.mutate(folder)}
              onRemove={() => remove.mutate(folder.id)}
            />
          ))}
        </div>
      </section>
      <SyncTokenPanel />
      {Conversation ? <Conversation /> : null}
    </div>
  );
}
