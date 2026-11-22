import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { HandoffEditor } from "../../components/HandoffEditor";
import { HandoffPreview } from "../../components/HandoffPreview";
import { HandoffHistory } from "../HandoffHistory";
import { HandoffSource } from "../HandoffSource";
import { useProjectHandoffs } from "./useProjectHandoffs";

export function ProjectHandoffsPage() {
  const view = useProjectHandoffs();
  const { draft, proposed, saved } = view;
  const busy = view.preview.isPending || view.approve.isPending || view.download.isPending;
  const error = [view.projects, view.source, view.history, saved, view.preview, view.approve, view.download]
    .find((query) => query.error)?.error;
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("projectHandoffs.title")}</h1>
      <p className="text-muted-foreground">{t("projectHandoffs.intro")}</p>
      <label className="grid max-w-md gap-1">
        {t("projectHandoffs.project")}
        <select className="rounded border bg-background p-2" value={draft.project_id} disabled={busy}
          onChange={(event) => view.chooseProject(event.target.value)}>
          <option value="">{t("projectHandoffs.chooseProject")}</option>
          {view.projects.data?.map(({ id, title }) => <option key={id} value={id}>{title}</option>)}
        </select>
      </label>
      {view.source.data && (
        <>
          <HandoffSource source={view.source.data} />
          <HandoffEditor draft={draft} busy={busy} onPreview={() => view.preview.mutate(draft)}
            onEdit={(field, value) => view.setDraft((previous) => ({ ...previous, [field]: value }))} />
        </>
      )}
      {proposed && (
        <HandoffPreview guide={proposed} busy={busy} onApprove={() => view.approve.mutate({
          ...draft, approved: true, expected_digest: proposed.digest,
        })} />
      )}
      {saved.data && (
        <HandoffPreview guide={saved.data} busy={busy} onExport={() => view.download.mutate(view.guideId)} />
      )}
      {error && <InlineError message={errorMessage(error)} />}
      {(view.projects.isPending || view.source.isFetching || saved.isFetching || busy) && <LoadingState />}
      {view.history.data && <HandoffHistory guides={view.history.data} currentId={view.guideId} />}
    </section>
  );
}
