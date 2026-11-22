import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ManifestPreview } from "../ManifestPreview";
import { PacketHistory } from "../PacketHistory";
import { PacketSelector } from "../PacketSelector";
import { useProofPackets } from "./useProofPackets";

function focusManifest() {
  requestAnimationFrame(() => document.getElementById("proof-manifest")?.focus());
}

export function ProofPacketsPage() {
  const view = useProofPackets();
  const proposed = view.proposed;
  const stored = view.stored;
  const visible = stored ?? proposed;
  const busy = [view.preview, view.save, view.open, view.download].some((request) => request.isPending);
  const error = [view.sources, view.history, view.preview, view.save, view.open, view.download]
    .find((request) => request.error)?.error;
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("proofPackets.title")}</h1>
      <p className="text-muted-foreground">{t("proofPackets.intro")}</p>
      {view.sources.data && (
        <PacketSelector selection={view.selection} sources={view.sources.data} busy={busy}
          onTitle={view.setTitle} onToggle={view.toggleSource}
          onPreview={() => view.preview.mutate(view.selection, { onSuccess: focusManifest })}
        />
      )}
      {visible && (
        <ManifestPreview manifest={visible.manifest} digest={visible.digest} busy={busy}
          onSave={proposed && !stored ? () => view.save.mutate({
            ...view.selection, expected_digest: proposed.digest,
          }, { onSuccess: focusManifest }) : undefined}
          onExport={stored ? () => view.download.mutate(stored.id) : undefined}
        />
      )}
      {view.save.isSuccess && <p role="status">{t("proofPackets.saved")}</p>}
      {error && <InlineError message={errorMessage(error)} />}
      {(view.sources.isPending || view.history.isPending) && <LoadingState />}
      {view.history.data && (
        <PacketHistory entries={view.history.data} busy={busy}
          onOpen={(id) => view.open.mutate(id, { onSuccess: focusManifest })}
        />
      )}
    </section>
  );
}
