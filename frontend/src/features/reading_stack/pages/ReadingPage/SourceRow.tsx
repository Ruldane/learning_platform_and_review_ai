import { AlertDialog } from "radix-ui";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ReadingSource } from "../../api";

interface SourceRowProps {
  source: ReadingSource;
  busy: boolean;
  onToggle: () => void;
  onRemove: () => void;
}

export function SourceRow({ source, busy, onToggle, onRemove }: SourceRowProps) {
  return (
    <li className="flex min-w-0 flex-col gap-2 rounded-md border p-3">
      <p className="break-words text-sm font-medium">{source.label}</p>
      <p className="break-all text-sm text-muted-foreground">{source.value}</p>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" disabled={busy} onClick={onToggle}>
          {t(source.active ? "reading.sources.pause" : "reading.sources.enable", {
            label: source.label,
          })}
        </Button>
        <AlertDialog.Root>
          <AlertDialog.Trigger asChild>
            <Button variant="outline" size="sm" disabled={busy}>
              {t("reading.sources.remove", { label: source.label })}
            </Button>
          </AlertDialog.Trigger>
          <AlertDialog.Portal>
            <AlertDialog.Overlay className="fixed inset-0 z-50 bg-black/45" />
            <AlertDialog.Content
              aria-describedby={undefined}
              className="fixed top-1/2 left-1/2 z-50 flex w-[min(90vw,27rem)] -translate-1/2 flex-col gap-3 rounded-xl border bg-background p-5 shadow-xl"
            >
              <AlertDialog.Title className="font-semibold">
                {t("reading.sources.removeAsk")}
              </AlertDialog.Title>
              <div className="flex flex-wrap justify-end gap-2">
                <AlertDialog.Cancel asChild>
                  <Button variant="outline">{t("reading.sources.cancel")}</Button>
                </AlertDialog.Cancel>
                <AlertDialog.Action asChild>
                  <Button variant="destructive" onClick={onRemove}>
                    {t("reading.sources.removeConfirm")}
                  </Button>
                </AlertDialog.Action>
              </div>
            </AlertDialog.Content>
          </AlertDialog.Portal>
        </AlertDialog.Root>
      </div>
    </li>
  );
}
