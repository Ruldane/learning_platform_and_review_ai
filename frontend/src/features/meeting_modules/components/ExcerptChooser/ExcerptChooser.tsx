import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Entry {
  line: number;
  kind: "decision" | "topic";
  text: string;
}

interface Props {
  excerpts: readonly Entry[];
  selection: readonly number[];
  busy: boolean;
  onToggle: (line: number) => void;
  onPreview: () => void;
}

export function ExcerptChooser({ excerpts, selection, busy, onToggle, onPreview }: Props) {
  return (
    <fieldset className="grid gap-3">
      <legend className="mb-2 font-semibold">{t("meetingModules.lines")}</legend>
      {excerpts.map((excerpt) => {
        const checked = selection.includes(excerpt.line);
        return (
          <label
            className="flex cursor-pointer items-start gap-3 rounded border p-3"
            key={excerpt.line}
          >
            <input
              type="checkbox"
              className="mt-1"
              checked={checked}
              disabled={busy || (!checked && selection.length >= 6)}
              onChange={() => onToggle(excerpt.line)}
            />
            <span className="grid gap-1">
              <span className="text-sm font-medium">
                {t(`meetingModules.${excerpt.kind}`)} ·{" "}
                {t("meetingModules.line", { line: excerpt.line })}
              </span>
              <span className="break-words">{excerpt.text}</span>
            </span>
          </label>
        );
      })}
      <Button type="button" aria-disabled={busy} onClick={() => !busy && onPreview()}>
        {t("meetingModules.preview")}
      </Button>
    </fieldset>
  );
}
