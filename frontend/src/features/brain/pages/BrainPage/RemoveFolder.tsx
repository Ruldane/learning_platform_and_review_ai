import { AlertDialog } from "radix-ui";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function RemoveFolder({
  name,
  busy,
  onRemove,
}: {
  name: string;
  busy: boolean;
  onRemove: () => void;
}) {
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>
        <Button type="button" size="sm" variant="destructive" disabled={busy}>
          {t("brain.remove")}
        </Button>
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-black/45" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 flex w-[min(90vw,27rem)] -translate-1/2 flex-col gap-3 rounded-xl border border-border bg-background p-5 shadow-xl">
          <AlertDialog.Title className="text-lg font-semibold">
            {t("brain.removeTitle", { name })}
          </AlertDialog.Title>
          <AlertDialog.Description className="text-sm text-muted-foreground">
            {t("brain.removeDetail")}
          </AlertDialog.Description>
          <div className="flex flex-wrap justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button type="button" variant="outline">
                {t("brain.cancel")}
              </Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button type="button" variant="destructive" onClick={onRemove}>
                {t("brain.remove")}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
