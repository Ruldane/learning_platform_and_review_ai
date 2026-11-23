import { AlertDialog } from "radix-ui";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function ConversationRemoval({
  action,
  busy,
  onConfirm,
}: {
  action: "clear" | "delete" | "wipe";
  busy: boolean;
  onConfirm: () => void;
}) {
  const label = t(`conversations.list.${action}`);
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>
        <Button type="button" size="sm" variant="outline" disabled={busy}>
          {label}
        </Button>
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-black/45" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 flex w-[min(90vw,27rem)] -translate-1/2 flex-col gap-3 rounded-xl border border-border bg-background p-5 shadow-xl">
          <AlertDialog.Title className="text-lg font-semibold">{label}</AlertDialog.Title>
          <AlertDialog.Description className="text-sm text-muted-foreground">
            {t(`conversations.list.${action}Hint`)}
          </AlertDialog.Description>
          <div className="flex flex-wrap justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button type="button" variant="outline">
                {t("conversations.list.cancel")}
              </Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button type="button" variant="destructive" onClick={onConfirm}>
                {t("conversations.list.confirm")}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
