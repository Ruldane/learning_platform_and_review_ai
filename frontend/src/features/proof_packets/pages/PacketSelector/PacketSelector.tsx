import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Selection, Source } from "../../api";

interface Props {
  selection: Selection;
  sources: Source[];
  onTitle: (title: string) => void;
  onToggle: (source: Source) => void;
  onPreview: () => void;
  busy: boolean;
}

export function PacketSelector({ selection, sources, onTitle, onToggle, onPreview, busy }: Props) {
  const selected = new Set(selection.sources.map((source) => source.proof_id));
  return (
    <form className="flex flex-col gap-3" onSubmit={(event) => { event.preventDefault(); onPreview(); }}>
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("proofPackets.name")}</span>
        <input
          className="rounded-md border border-input bg-background p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          required maxLength={120} value={selection.title}
          onChange={(event) => onTitle(event.target.value)}
        />
      </label>
      <fieldset className="flex flex-col gap-2 rounded-lg border border-border p-3">
        <legend className="px-1 font-semibold">{t("proofPackets.sources")}</legend>
        {sources.length === 0 && <p>{t("proofPackets.noSources")}</p>}
        {sources.map((source) => (
          <label className="flex gap-2 p-1" key={source.proof_id}>
            <input
              type="checkbox"
              checked={selected.has(source.proof_id)}
              disabled={selected.size >= 12 && !selected.has(source.proof_id)}
              onChange={() => onToggle(source)}
            />
            <span>{t("proofPackets.source", { title: source.title, revision: source.revision })}</span>
            <span className="text-sm text-muted-foreground">{source.proof_id.slice(0, 8)}</span>
          </label>
        ))}
      </fieldset>
      <Button type="submit" className="self-start"
        disabled={busy || !selection.title.trim() || !selected.size}>
        {t("proofPackets.preview")}
      </Button>
    </form>
  );
}
